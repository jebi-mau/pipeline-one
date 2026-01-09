import { useState } from 'react'
import { Link } from 'react-router-dom'
import { PlusIcon } from '@heroicons/react/24/outline'

// Placeholder jobs data
const mockJobs = [
  {
    id: '1',
    name: 'Mining Site Analysis',
    status: 'completed',
    progress: 100,
    createdAt: '2024-01-15T10:30:00Z',
    totalFrames: 1200,
    detections: 3456,
  },
  {
    id: '2',
    name: 'Equipment Detection',
    status: 'running',
    progress: 45,
    createdAt: '2024-01-15T14:20:00Z',
    totalFrames: 800,
    detections: 1234,
  },
]

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-500',
  running: 'bg-blue-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
  cancelled: 'bg-gray-500',
}

export default function JobsPage() {
  const [jobs] = useState(mockJobs)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-secondary-100">Processing Jobs</h1>
        <Link to="/jobs/new" className="btn-primary">
          <PlusIcon className="w-5 h-5 mr-2" />
          New Job
        </Link>
      </div>

      {/* Jobs List */}
      <div className="card overflow-hidden">
        <table className="w-full">
          <thead className="bg-secondary-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                Progress
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                Frames
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                Detections
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                Created
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-secondary-700">
            {jobs.map((job) => (
              <tr
                key={job.id}
                className="hover:bg-secondary-700/50 cursor-pointer"
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <Link
                    to={`/jobs/${job.id}`}
                    className="text-sm font-medium text-secondary-100 hover:text-primary-400"
                  >
                    {job.name}
                  </Link>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      statusColors[job.status]
                    } text-white`}
                  >
                    {job.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="w-full bg-secondary-600 rounded-full h-2">
                    <div
                      className="bg-primary-500 h-2 rounded-full"
                      style={{ width: `${job.progress}%` }}
                    />
                  </div>
                  <span className="text-xs text-secondary-400 mt-1">
                    {job.progress}%
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-300">
                  {job.totalFrames.toLocaleString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-300">
                  {job.detections.toLocaleString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-400">
                  {new Date(job.createdAt).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
