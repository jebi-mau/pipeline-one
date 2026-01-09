import { Outlet, NavLink } from 'react-router-dom'
import {
  HomeIcon,
  FolderIcon,
  Cog6ToothIcon,
  DocumentDuplicateIcon,
} from '@heroicons/react/24/outline'
import { clsx } from 'clsx'

const navigation = [
  { name: 'Home', href: '/', icon: HomeIcon },
  { name: 'Jobs', href: '/jobs', icon: DocumentDuplicateIcon },
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
]

export default function MainLayout() {
  return (
    <div className="flex h-screen bg-secondary-900">
      {/* Sidebar */}
      <div className="w-64 flex flex-col bg-secondary-800 border-r border-secondary-700">
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b border-secondary-700">
          <span className="text-xl font-bold text-primary-500">SVO2-SAM3</span>
          <span className="ml-2 text-sm text-secondary-400">Analyzer</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-4 space-y-1">
          {navigation.map((item) => (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive }) =>
                clsx(
                  'flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                  isActive
                    ? 'bg-primary-600/20 text-primary-400'
                    : 'text-secondary-300 hover:bg-secondary-700 hover:text-secondary-100'
                )
              }
            >
              <item.icon className="w-5 h-5 mr-3" />
              {item.name}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-4 border-t border-secondary-700">
          <div className="text-xs text-secondary-500">
            <p>JEBI S.A.C.</p>
            <p>Version 1.0.0</p>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 flex items-center justify-between px-6 bg-secondary-800 border-b border-secondary-700">
          <h1 className="text-lg font-semibold text-secondary-100">
            SVO2-SAM3 Analyzer
          </h1>
          <div className="flex items-center space-x-4">
            <span className="text-sm text-secondary-400">
              100% Local Processing
            </span>
            <div className="w-2 h-2 bg-green-500 rounded-full" title="System Ready" />
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
