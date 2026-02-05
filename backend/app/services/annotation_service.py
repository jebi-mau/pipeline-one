"""Annotation import and export service for CVAT and other tools."""

import json
import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.dataset import Dataset
from backend.app.models.external_annotation import AnnotationImport, ExternalAnnotation
from backend.app.models.frame import Frame
from backend.app.schemas.annotation import (
    AnnotationImportDetail,
    AnnotationImportResponse,
    AnnotationImportSummary,
    AnnotationMatchStats,
    ExternalAnnotationDetail,
    ExternalAnnotationSummary,
    FrameAnnotationsResponse,
)

logger = logging.getLogger(__name__)

OUTPUT_BASE = Path(os.getenv("PIPELINE_OUTPUT_DIR", "data/output"))


class AnnotationService:
    """Service for importing and managing external annotations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def import_annotations(
        self,
        dataset_id: UUID,
        source_path: str,
        source_tool: str = "cvat",
        source_format: str = "xml",
        match_by: str = "filename",
    ) -> AnnotationImportResponse:
        """Import annotations from external tool."""
        # Verify dataset exists
        result = await self.db.execute(
            select(Dataset).where(Dataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if dataset is None:
            raise ValueError(f"Dataset {dataset_id} not found")

        source_file = Path(source_path)
        if not source_file.exists():
            raise ValueError(f"Annotation file not found: {source_path}")

        # Create import record
        annotation_import = AnnotationImport(
            dataset_id=dataset_id,
            source_tool=source_tool,
            source_format=source_format,
            source_path=source_path,
            source_filename=source_file.name,
            status="processing",
            imported_at=datetime.now(timezone.utc),
        )
        self.db.add(annotation_import)
        await self.db.flush()

        try:
            # Parse annotations based on format
            if source_format == "xml" and source_tool == "cvat":
                annotations_data = self._parse_cvat_xml(source_file)
            elif source_format == "json" and source_tool == "cvat":
                annotations_data = self._parse_cvat_json(source_file)
            elif source_format == "coco":
                annotations_data = self._parse_coco_json(source_file)
            else:
                raise ValueError(f"Unsupported format: {source_tool}/{source_format}")

            # Store annotations
            total_annotations = 0
            total_images = len(annotations_data)

            for image_name, image_annotations in annotations_data.items():
                for ann in image_annotations:
                    ext_ann = ExternalAnnotation(
                        import_id=annotation_import.id,
                        source_image_name=image_name,
                        label=ann["label"],
                        annotation_type=ann["type"],
                        bbox_x=ann.get("bbox_x"),
                        bbox_y=ann.get("bbox_y"),
                        bbox_width=ann.get("bbox_width"),
                        bbox_height=ann.get("bbox_height"),
                        points=ann.get("points"),
                        attributes=ann.get("attributes"),
                        occurrence_id=ann.get("occurrence_id"),
                        z_order=ann.get("z_order", 0),
                    )
                    self.db.add(ext_ann)
                    total_annotations += 1

            # Update import record
            annotation_import.total_images = total_images
            annotation_import.total_annotations = total_annotations
            annotation_import.import_metadata = {
                "source_tool": source_tool,
                "source_format": source_format,
                "labels": list({
                    ann["label"]
                    for anns in annotations_data.values()
                    for ann in anns
                }),
            }

            await self.db.commit()

            # Match annotations to frames
            matched = await self._match_annotations(
                annotation_import.id, dataset_id, match_by
            )

            # Update final status
            annotation_import.status = "completed"
            annotation_import.matched_frames = matched
            annotation_import.unmatched_images = total_images - matched
            annotation_import.completed_at = datetime.now(timezone.utc)
            await self.db.commit()

            logger.info(
                f"Imported {total_annotations} annotations from {source_file.name}, "
                f"matched {matched}/{total_images} images"
            )

            return AnnotationImportResponse(
                import_id=annotation_import.id,
                dataset_id=dataset_id,
                status="completed",
                message=f"Imported {total_annotations} annotations, matched {matched} images",
                total_images=total_images,
                total_annotations=total_annotations,
            )

        except Exception as e:
            annotation_import.status = "failed"
            annotation_import.error_message = str(e)
            await self.db.commit()

            logger.error(f"Failed to import annotations: {e}")
            raise

    def _parse_cvat_xml(self, file_path: Path) -> dict[str, list[dict]]:
        """Parse CVAT XML annotation format."""
        tree = ET.parse(file_path)
        root = tree.getroot()

        annotations: dict[str, list[dict]] = {}

        # CVAT XML structure: <annotations><image name="..."><box>...</box></image></annotations>
        for image in root.findall(".//image"):
            image_name = image.get("name", "")
            annotations[image_name] = []

            # Parse boxes
            for box in image.findall("box"):
                ann = {
                    "type": "bbox",
                    "label": box.get("label", "unknown"),
                    "bbox_x": float(box.get("xtl", 0)),
                    "bbox_y": float(box.get("ytl", 0)),
                    "bbox_width": float(box.get("xbr", 0)) - float(box.get("xtl", 0)),
                    "bbox_height": float(box.get("ybr", 0)) - float(box.get("ytl", 0)),
                    "occurrence_id": int(box.get("occluded", 0)),
                    "z_order": int(box.get("z_order", 0)),
                    "attributes": {},
                }

                # Parse attributes
                for attr in box.findall("attribute"):
                    attr_name = attr.get("name", "")
                    ann["attributes"][attr_name] = attr.text

                annotations[image_name].append(ann)

            # Parse polygons
            for polygon in image.findall("polygon"):
                points_str = polygon.get("points", "")
                points = [
                    [float(x) for x in p.split(",")]
                    for p in points_str.split(";")
                    if p
                ]

                ann = {
                    "type": "polygon",
                    "label": polygon.get("label", "unknown"),
                    "points": points,
                    "z_order": int(polygon.get("z_order", 0)),
                    "attributes": {},
                }

                for attr in polygon.findall("attribute"):
                    attr_name = attr.get("name", "")
                    ann["attributes"][attr_name] = attr.text

                annotations[image_name].append(ann)

            # Parse polylines
            for polyline in image.findall("polyline"):
                points_str = polyline.get("points", "")
                points = [
                    [float(x) for x in p.split(",")]
                    for p in points_str.split(";")
                    if p
                ]

                ann = {
                    "type": "polyline",
                    "label": polyline.get("label", "unknown"),
                    "points": points,
                    "z_order": int(polyline.get("z_order", 0)),
                    "attributes": {},
                }

                annotations[image_name].append(ann)

            # Parse points
            for points_elem in image.findall("points"):
                points_str = points_elem.get("points", "")
                points = [
                    [float(x) for x in p.split(",")]
                    for p in points_str.split(";")
                    if p
                ]

                ann = {
                    "type": "points",
                    "label": points_elem.get("label", "unknown"),
                    "points": points,
                    "z_order": int(points_elem.get("z_order", 0)),
                    "attributes": {},
                }

                annotations[image_name].append(ann)

        return annotations

    def _parse_cvat_json(self, file_path: Path) -> dict[str, list[dict]]:
        """Parse CVAT JSON annotation format."""
        with open(file_path) as f:
            data = json.load(f)

        annotations: dict[str, list[dict]] = {}

        # CVAT JSON structure varies - handle common formats
        for item in data.get("annotations", data.get("images", [])):
            image_name = item.get("name", item.get("file_name", ""))
            annotations[image_name] = []

            for shape in item.get("shapes", item.get("annotations", [])):
                ann = {
                    "type": shape.get("type", "bbox"),
                    "label": shape.get("label", "unknown"),
                    "z_order": shape.get("z_order", 0),
                    "attributes": shape.get("attributes", {}),
                }

                if ann["type"] == "rectangle" or ann["type"] == "bbox":
                    ann["type"] = "bbox"
                    points = shape.get("points", [])
                    if len(points) >= 4:
                        ann["bbox_x"] = points[0]
                        ann["bbox_y"] = points[1]
                        ann["bbox_width"] = points[2] - points[0]
                        ann["bbox_height"] = points[3] - points[1]
                else:
                    ann["points"] = shape.get("points", [])

                annotations[image_name].append(ann)

        return annotations

    def _parse_coco_json(self, file_path: Path) -> dict[str, list[dict]]:
        """Parse COCO JSON annotation format."""
        with open(file_path) as f:
            data = json.load(f)

        annotations: dict[str, list[dict]] = {}

        # Build image ID to filename mapping
        image_map = {img["id"]: img["file_name"] for img in data.get("images", [])}

        # Build category ID to name mapping
        category_map = {
            cat["id"]: cat["name"] for cat in data.get("categories", [])
        }

        # Parse annotations
        for ann in data.get("annotations", []):
            image_id = ann.get("image_id")
            image_name = image_map.get(image_id, f"image_{image_id}")

            if image_name not in annotations:
                annotations[image_name] = []

            category_id = ann.get("category_id")
            label = category_map.get(category_id, f"category_{category_id}")

            bbox = ann.get("bbox", [])
            if len(bbox) >= 4:
                parsed_ann = {
                    "type": "bbox",
                    "label": label,
                    "bbox_x": bbox[0],
                    "bbox_y": bbox[1],
                    "bbox_width": bbox[2],
                    "bbox_height": bbox[3],
                    "attributes": {
                        "area": ann.get("area"),
                        "iscrowd": ann.get("iscrowd", 0),
                    },
                }
                annotations[image_name].append(parsed_ann)

            # Handle segmentation if present
            segmentation = ann.get("segmentation")
            if segmentation and isinstance(segmentation, list) and len(segmentation) > 0:
                if isinstance(segmentation[0], list):
                    # Polygon format
                    for poly in segmentation:
                        points = [[poly[i], poly[i + 1]] for i in range(0, len(poly), 2)]
                        parsed_ann = {
                            "type": "polygon",
                            "label": label,
                            "points": points,
                            "attributes": {"area": ann.get("area")},
                        }
                        annotations[image_name].append(parsed_ann)

        return annotations

    async def _match_annotations(
        self,
        import_id: UUID,
        dataset_id: UUID,
        match_by: str = "filename",
    ) -> int:
        """Match imported annotations to existing frames."""
        # Get all frames for jobs linked to this dataset
        result = await self.db.execute(
            select(Frame)
            .join(Frame.job)
            .where(Frame.job.has(dataset_id=dataset_id))
        )
        frames = result.scalars().all()

        # Build lookup maps
        if match_by == "filename":
            # Map by image filename (e.g., "000000.png" -> frame_id)
            frame_lookup = {}
            for frame in frames:
                if frame.image_left_path:
                    filename = Path(frame.image_left_path).name
                    frame_lookup[filename] = frame.id
                    # Also try without extension
                    frame_lookup[Path(filename).stem] = frame.id
        else:
            # Map by frame index
            frame_lookup = {
                str(frame.svo2_frame_index): frame.id for frame in frames
            }

        # Match annotations
        matched_count = 0
        ext_anns = await self.db.execute(
            select(ExternalAnnotation).where(ExternalAnnotation.import_id == import_id)
        )

        for ext_ann in ext_anns.scalars().all():
            # Try to match by source image name
            image_name = ext_ann.source_image_name
            frame_id = frame_lookup.get(image_name)

            # Try without path
            if frame_id is None:
                filename = Path(image_name).name
                frame_id = frame_lookup.get(filename)

            # Try without extension
            if frame_id is None:
                stem = Path(image_name).stem
                frame_id = frame_lookup.get(stem)

            if frame_id:
                ext_ann.frame_id = frame_id
                ext_ann.is_matched = True
                ext_ann.match_confidence = 1.0
                matched_count += 1

        await self.db.commit()
        return matched_count

    async def list_imports(
        self,
        dataset_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[AnnotationImportSummary], int]:
        """List annotation imports for a dataset."""
        query = select(AnnotationImport).where(
            AnnotationImport.dataset_id == dataset_id
        )
        count_query = select(func.count(AnnotationImport.id)).where(
            AnnotationImport.dataset_id == dataset_id
        )

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        query = query.order_by(AnnotationImport.created_at.desc())
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)

        imports = [
            AnnotationImportSummary(
                id=imp.id,
                dataset_id=imp.dataset_id,
                source_tool=imp.source_tool,
                source_format=imp.source_format,
                source_filename=imp.source_filename,
                status=imp.status,
                total_images=imp.total_images,
                matched_frames=imp.matched_frames,
                unmatched_images=imp.unmatched_images,
                total_annotations=imp.total_annotations,
                imported_at=imp.imported_at,
                completed_at=imp.completed_at,
                error_message=imp.error_message,
                created_at=imp.created_at,
            )
            for imp in result.scalars().all()
        ]

        return imports, total

    async def get_import_detail(
        self, import_id: UUID
    ) -> AnnotationImportDetail | None:
        """Get annotation import details."""
        result = await self.db.execute(
            select(AnnotationImport).where(AnnotationImport.id == import_id)
        )
        imp = result.scalar_one_or_none()
        if imp is None:
            return None

        return AnnotationImportDetail(
            id=imp.id,
            dataset_id=imp.dataset_id,
            source_tool=imp.source_tool,
            source_format=imp.source_format,
            source_filename=imp.source_filename,
            source_path=imp.source_path,
            status=imp.status,
            total_images=imp.total_images,
            matched_frames=imp.matched_frames,
            unmatched_images=imp.unmatched_images,
            total_annotations=imp.total_annotations,
            imported_at=imp.imported_at,
            completed_at=imp.completed_at,
            error_message=imp.error_message,
            import_metadata=imp.import_metadata,
            created_at=imp.created_at,
            updated_at=imp.updated_at,
        )

    async def list_annotations(
        self,
        import_id: UUID,
        matched_only: bool = False,
        label: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[ExternalAnnotationSummary], int, int, int]:
        """List external annotations with filtering."""
        query = select(ExternalAnnotation).where(
            ExternalAnnotation.import_id == import_id
        )
        count_query = select(func.count(ExternalAnnotation.id)).where(
            ExternalAnnotation.import_id == import_id
        )

        if matched_only:
            query = query.where(ExternalAnnotation.is_matched.is_(True))
        if label:
            query = query.where(ExternalAnnotation.label == label)
            count_query = count_query.where(ExternalAnnotation.label == label)

        # Get counts
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        matched_count_result = await self.db.execute(
            select(func.count(ExternalAnnotation.id))
            .where(ExternalAnnotation.import_id == import_id)
            .where(ExternalAnnotation.is_matched.is_(True))
        )
        matched = matched_count_result.scalar() or 0
        unmatched = total - matched

        # Get paginated results
        query = query.order_by(ExternalAnnotation.source_image_name)
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)

        annotations = [
            ExternalAnnotationSummary(
                id=ann.id,
                frame_id=ann.frame_id,
                source_image_name=ann.source_image_name,
                label=ann.label,
                annotation_type=ann.annotation_type,
                bbox=(ann.bbox_x, ann.bbox_y, ann.bbox_width, ann.bbox_height)
                if ann.bbox_x is not None
                else None,
                is_matched=ann.is_matched,
            )
            for ann in result.scalars().all()
        ]

        return annotations, total, matched, unmatched

    async def get_frame_annotations(
        self, frame_id: UUID
    ) -> FrameAnnotationsResponse | None:
        """Get all external annotations for a frame."""
        result = await self.db.execute(
            select(ExternalAnnotation).where(ExternalAnnotation.frame_id == frame_id)
        )
        annotations = result.scalars().all()

        details = [
            ExternalAnnotationDetail(
                id=ann.id,
                import_id=ann.import_id,
                frame_id=ann.frame_id,
                source_image_name=ann.source_image_name,
                label=ann.label,
                annotation_type=ann.annotation_type,
                bbox_x=ann.bbox_x,
                bbox_y=ann.bbox_y,
                bbox_width=ann.bbox_width,
                bbox_height=ann.bbox_height,
                points=ann.points,
                attributes=ann.attributes,
                occurrence_id=ann.occurrence_id,
                z_order=ann.z_order,
                is_matched=ann.is_matched,
                match_confidence=ann.match_confidence,
                created_at=ann.created_at,
                updated_at=ann.updated_at,
            )
            for ann in annotations
        ]

        return FrameAnnotationsResponse(
            frame_id=frame_id,
            annotations=details,
            total=len(details),
        )

    async def get_match_stats(self, import_id: UUID) -> AnnotationMatchStats | None:
        """Get matching statistics for an import."""
        result = await self.db.execute(
            select(AnnotationImport).where(AnnotationImport.id == import_id)
        )
        imp = result.scalar_one_or_none()
        if imp is None:
            return None

        # Count by label
        label_counts = await self.db.execute(
            select(ExternalAnnotation.label, func.count(ExternalAnnotation.id))
            .where(ExternalAnnotation.import_id == import_id)
            .group_by(ExternalAnnotation.label)
        )
        labels = {row[0]: row[1] for row in label_counts.all()}

        matched = imp.matched_frames
        total = imp.total_annotations

        return AnnotationMatchStats(
            import_id=import_id,
            total_annotations=total,
            matched_annotations=matched,
            unmatched_annotations=total - matched,
            match_rate=matched / total if total > 0 else 0.0,
            labels=labels,
        )

    async def delete_import(self, import_id: UUID) -> bool:
        """Delete an annotation import and its annotations."""
        result = await self.db.execute(
            select(AnnotationImport).where(AnnotationImport.id == import_id)
        )
        imp = result.scalar_one_or_none()
        if imp is None:
            return False

        await self.db.delete(imp)
        await self.db.commit()

        logger.info(f"Deleted annotation import {import_id}")
        return True
