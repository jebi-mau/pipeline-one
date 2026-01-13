/**
 * Pipeline One - Annotated Image component with bounding box overlay and mask support
 */

import { useRef, useEffect, useState, useCallback } from 'react';
import type { AnnotationSummary } from '../../types/data';

interface AnnotatedImageProps {
  imageUrl: string;
  annotations: AnnotationSummary[];
  showBoxes?: boolean;
  showLabels?: boolean;
  showMasks?: boolean;
  selectedAnnotationId?: string | null;
  onSelectAnnotation?: (annotationId: string | null) => void;
}

interface MaskCache {
  [key: string]: HTMLImageElement | null;
}

export function AnnotatedImage({
  imageUrl,
  annotations,
  showBoxes = true,
  showLabels = true,
  showMasks = true,
  selectedAnnotationId = null,
  onSelectAnnotation,
}: AnnotatedImageProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  const [maskCache, setMaskCache] = useState<MaskCache>({});
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  // Handle image load to get dimensions
  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    setImageDimensions({ width: img.naturalWidth, height: img.naturalHeight });
    setImageLoaded(true);
  };

  // Update container size on resize
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setContainerSize({ width: rect.width, height: rect.height });
      }
    };

    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  // Calculate scale and offset for proper alignment
  useEffect(() => {
    if (imageDimensions.width > 0 && containerSize.width > 0) {
      const scaleX = containerSize.width / imageDimensions.width;
      const scaleY = containerSize.height / imageDimensions.height;
      const newScale = Math.min(scaleX, scaleY);
      setScale(newScale);

      // Calculate offset to center the image
      const displayWidth = imageDimensions.width * newScale;
      const displayHeight = imageDimensions.height * newScale;
      setOffset({
        x: (containerSize.width - displayWidth) / 2,
        y: (containerSize.height - displayHeight) / 2,
      });
    }
  }, [imageDimensions, containerSize]);

  // Load masks when annotations change
  useEffect(() => {
    if (!showMasks) return;

    const loadMask = async (ann: AnnotationSummary) => {
      if (!ann.mask_url) return;
      if (maskCache[ann.id]) return; // Already loaded

      try {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        await new Promise<void>((resolve, reject) => {
          img.onload = () => resolve();
          img.onerror = () => reject();
          img.src = ann.mask_url!;
        });
        setMaskCache(prev => ({ ...prev, [ann.id]: img }));
      } catch {
        setMaskCache(prev => ({ ...prev, [ann.id]: null }));
      }
    };

    annotations.forEach(ann => {
      if (ann.mask_url && !maskCache[ann.id]) {
        loadMask(ann);
      }
    });
  }, [annotations, showMasks, maskCache]);

  // Handle click on canvas to select annotations
  const handleCanvasClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!onSelectAnnotation || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const clickX = (e.clientX - rect.left - offset.x) / scale;
    const clickY = (e.clientY - rect.top - offset.y) / scale;

    // Check if click is inside any annotation (check from last to first for z-order)
    for (let i = annotations.length - 1; i >= 0; i--) {
      const ann = annotations[i];
      const { bbox_2d } = ann;

      if (
        clickX >= bbox_2d.x &&
        clickX <= bbox_2d.x + bbox_2d.width &&
        clickY >= bbox_2d.y &&
        clickY <= bbox_2d.y + bbox_2d.height
      ) {
        // Toggle selection if clicking same annotation
        if (selectedAnnotationId === ann.id) {
          onSelectAnnotation(null);
        } else {
          onSelectAnnotation(ann.id);
        }
        return;
      }
    }

    // Clicked outside all annotations - deselect
    onSelectAnnotation(null);
  }, [annotations, scale, offset, selectedAnnotationId, onSelectAnnotation]);

  // Draw annotations on canvas
  useEffect(() => {
    if (!canvasRef.current || !imageLoaded) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size to match container
    canvas.width = containerSize.width;
    canvas.height = containerSize.height;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!showBoxes && !showMasks) return;

    // Draw each annotation
    annotations.forEach((ann) => {
      const { bbox_2d, class_color, confidence } = ann;
      const isSelected = selectedAnnotationId === ann.id;

      // Scale and offset coordinates
      const x = bbox_2d.x * scale + offset.x;
      const y = bbox_2d.y * scale + offset.y;
      const width = bbox_2d.width * scale;
      const height = bbox_2d.height * scale;

      // Draw mask if available and enabled
      if (showMasks && ann.mask_url && maskCache[ann.id]) {
        const maskImg = maskCache[ann.id]!;

        // Create temporary canvas to colorize mask
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = maskImg.width;
        tempCanvas.height = maskImg.height;
        const tempCtx = tempCanvas.getContext('2d');

        if (tempCtx) {
          // Draw mask
          tempCtx.drawImage(maskImg, 0, 0);

          // Get mask data and colorize
          const imageData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
          const data = imageData.data;

          // Parse color
          const r = parseInt(class_color.slice(1, 3), 16);
          const g = parseInt(class_color.slice(3, 5), 16);
          const b = parseInt(class_color.slice(5, 7), 16);
          const alpha = isSelected ? 0.6 : 0.35;

          // Apply color to mask (mask is grayscale, use as alpha)
          for (let i = 0; i < data.length; i += 4) {
            const maskValue = data[i]; // Grayscale value
            if (maskValue > 128) {
              data[i] = r;
              data[i + 1] = g;
              data[i + 2] = b;
              data[i + 3] = Math.round(maskValue * alpha);
            } else {
              data[i + 3] = 0; // Transparent
            }
          }

          tempCtx.putImageData(imageData, 0, 0);

          // Draw colorized mask on main canvas
          ctx.drawImage(
            tempCanvas,
            offset.x,
            offset.y,
            imageDimensions.width * scale,
            imageDimensions.height * scale
          );
        }
      }

      // Draw bounding box
      if (showBoxes) {
        const lineWidth = isSelected ? 3 : 2;
        ctx.strokeStyle = class_color;
        ctx.lineWidth = lineWidth;
        ctx.strokeRect(x, y, width, height);

        // Draw semi-transparent fill for non-mask or selected
        if (!showMasks || !ann.mask_url || isSelected) {
          ctx.fillStyle = class_color + (isSelected ? '40' : '15');
          ctx.fillRect(x, y, width, height);
        }

        // Draw selection highlight
        if (isSelected) {
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 1;
          ctx.setLineDash([4, 4]);
          ctx.strokeRect(x - 2, y - 2, width + 4, height + 4);
          ctx.setLineDash([]);
        }

        // Draw label
        if (showLabels) {
          const distanceStr = ann.distance !== null ? ` ${ann.distance.toFixed(1)}m` : '';
          const label = `${ann.class_name} ${(confidence * 100).toFixed(0)}%${distanceStr}`;
          ctx.font = isSelected ? 'bold 12px sans-serif' : '12px sans-serif';
          const textMetrics = ctx.measureText(label);
          const labelHeight = 16;
          const labelPadding = 4;

          // Position label above box, or inside if too close to top
          const labelY = y > labelHeight + 4 ? y - labelHeight - 2 : y + 2;
          const labelX = x;

          // Background
          ctx.fillStyle = class_color;
          ctx.fillRect(
            labelX,
            labelY,
            textMetrics.width + labelPadding * 2,
            labelHeight
          );

          // Text
          ctx.fillStyle = '#ffffff';
          ctx.fillText(
            label,
            labelX + labelPadding,
            labelY + labelHeight - 4
          );
        }
      }
    });
  }, [
    annotations,
    imageLoaded,
    containerSize,
    imageDimensions,
    showBoxes,
    showLabels,
    showMasks,
    selectedAnnotationId,
    maskCache,
    scale,
    offset,
  ]);

  return (
    <div
      ref={containerRef}
      className="aspect-video bg-secondary-700 rounded-lg overflow-hidden relative"
    >
      <img
        src={imageUrl}
        alt="Frame"
        onLoad={handleImageLoad}
        className="w-full h-full object-contain"
      />
      {annotations.length > 0 && (
        <canvas
          ref={canvasRef}
          onClick={handleCanvasClick}
          className="absolute top-0 left-0 w-full h-full"
          style={{
            cursor: onSelectAnnotation ? 'pointer' : 'default',
          }}
        />
      )}
    </div>
  );
}
