import { Routes, Route } from 'react-router-dom'
import MainLayout from './components/layout/MainLayout'
import HomePage from './pages/HomePage'
import JobsPage from './pages/JobsPage'
import JobDetailPage from './pages/JobDetailPage'
import DatasetsPage from './pages/DatasetsPage'
import DatasetDetailPage from './pages/DatasetDetailPage'
import FrameDetailPage from './pages/FrameDetailPage'
import DataPage from './pages/DataPage'
import ReviewPage from './pages/ReviewPage'
import SettingsPage from './pages/SettingsPage'
import { ErrorBoundary } from './components/common'

function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<ErrorBoundary><HomePage /></ErrorBoundary>} />
          <Route path="jobs" element={<ErrorBoundary><JobsPage /></ErrorBoundary>} />
          <Route path="jobs/:jobId" element={<ErrorBoundary><JobDetailPage /></ErrorBoundary>} />
          <Route path="datasets" element={<ErrorBoundary><DatasetsPage /></ErrorBoundary>} />
          <Route path="datasets/:datasetId" element={<ErrorBoundary><DatasetDetailPage /></ErrorBoundary>} />
          <Route path="frames/:frameId" element={<ErrorBoundary><FrameDetailPage /></ErrorBoundary>} />
          <Route path="data" element={<ErrorBoundary><DataPage /></ErrorBoundary>} />
          <Route path="review" element={<ErrorBoundary><ReviewPage /></ErrorBoundary>} />
          <Route path="settings" element={<ErrorBoundary><SettingsPage /></ErrorBoundary>} />
        </Route>
      </Routes>
    </ErrorBoundary>
  )
}

export default App
