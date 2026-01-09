import { useParams } from 'react-router-dom'

export default function JobDetailPage() {
  const { jobId } = useParams()

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-secondary-100">Job Details</h1>
      <div className="card p-6">
        <p className="text-secondary-400">
          Job ID: <span className="text-secondary-100">{jobId}</span>
        </p>
        <p className="mt-4 text-secondary-400">
          Job detail view will be implemented here, including:
        </p>
        <ul className="mt-2 list-disc list-inside text-secondary-400">
          <li>Processing progress and stage indicators</li>
          <li>Frame viewer with detection overlays</li>
          <li>3D point cloud visualization</li>
          <li>Results statistics and charts</li>
          <li>Export options (KITTI, COCO, JSON)</li>
        </ul>
      </div>
    </div>
  )
}
