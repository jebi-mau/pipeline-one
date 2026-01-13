/**
 * Pipeline One - Workflow-oriented layout with pipeline navigation
 */

import { Outlet, NavLink, useLocation } from 'react-router-dom';
import {
  HomeIcon,
  Cog6ToothIcon,
  DocumentDuplicateIcon,
  CircleStackIcon,
  FolderIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';
import { clsx } from 'clsx';

// Workflow-oriented navigation structure
const pipelineSteps = [
  {
    name: '1. Datasets',
    description: 'Import SVO2',
    href: '/datasets',
    icon: FolderIcon,
  },
  {
    name: '2. Process',
    description: 'Extract & Detect',
    href: '/jobs',
    icon: DocumentDuplicateIcon,
  },
  {
    name: '3. Review',
    description: 'Filter & Export',
    href: '/review',
    icon: CircleStackIcon,
  },
];

const utilityNav = [
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
];

export default function MainLayout() {
  const location = useLocation();

  // Determine current pipeline step for progress indicator
  const getCurrentStep = () => {
    if (location.pathname.startsWith('/datasets')) return 0;
    if (location.pathname.startsWith('/jobs')) return 1;
    if (location.pathname.startsWith('/review')) return 2;
    if (location.pathname.startsWith('/data')) return 2; // Legacy data explorer
    return -1;
  };

  const currentStep = getCurrentStep();

  return (
    <div className="flex h-screen bg-secondary-900">
      {/* Sidebar */}
      <div className="w-72 flex flex-col bg-secondary-800 border-r border-secondary-700">
        {/* Logo */}
        <NavLink
          to="/"
          className="h-16 flex items-center px-6 border-b border-secondary-700 hover:bg-secondary-700/50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary-600 flex items-center justify-center">
              <span className="text-lg font-bold text-white">P1</span>
            </div>
            <div>
              <span className="text-lg font-bold text-primary-400">Pipeline One</span>
              <span className="text-xs block text-secondary-400">
                SVO2 → Training Data
              </span>
            </div>
          </div>
        </NavLink>

        {/* Pipeline Navigation */}
        <nav className="flex-1 px-4 py-4 space-y-6 overflow-y-auto">
          {/* Home Link */}
          <NavLink
            to="/"
            className={({ isActive }) =>
              clsx(
                'flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-colors',
                isActive
                  ? 'bg-primary-600/20 text-primary-400'
                  : 'text-secondary-300 hover:bg-secondary-700 hover:text-secondary-100'
              )
            }
          >
            <HomeIcon className="w-5 h-5 mr-3" />
            Dashboard
          </NavLink>

          {/* Pipeline Steps */}
          <div>
            <h3 className="px-3 text-xs font-semibold text-secondary-500 uppercase tracking-wider mb-3">
              Pipeline Workflow
            </h3>
            <div className="space-y-1">
              {pipelineSteps.map((item, index) => {
                const isActive = location.pathname.startsWith(item.href.split('?')[0]);
                const isPast = currentStep > index;
                const isCurrent = currentStep === index;

                return (
                  <NavLink
                    key={item.name}
                    to={item.href}
                    className={clsx(
                      'flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-colors relative',
                      isActive
                        ? 'bg-primary-600/20 text-primary-400'
                        : 'text-secondary-300 hover:bg-secondary-700 hover:text-secondary-100'
                    )}
                  >
                    {/* Step indicator line */}
                    {index < pipelineSteps.length - 1 && (
                      <div
                        className={clsx(
                          'absolute left-[26px] top-[40px] w-0.5 h-4',
                          isPast ? 'bg-primary-500' : 'bg-secondary-600'
                        )}
                      />
                    )}

                    {/* Step number circle */}
                    <div
                      className={clsx(
                        'w-5 h-5 rounded-full flex items-center justify-center mr-3 text-xs font-bold border',
                        isPast && 'bg-primary-600 border-primary-500 text-white',
                        isCurrent && 'bg-primary-600/30 border-primary-500 text-primary-400',
                        !isPast && !isCurrent && 'bg-secondary-700 border-secondary-600 text-secondary-400'
                      )}
                    >
                      {index + 1}
                    </div>

                    <div className="flex-1">
                      <span className="block">{item.name.split('. ')[1]}</span>
                      <span className="text-xs text-secondary-500">
                        {item.description}
                      </span>
                    </div>

                    {isActive && (
                      <ChevronRightIcon className="w-4 h-4 text-primary-400" />
                    )}
                  </NavLink>
                );
              })}
            </div>
          </div>

          {/* Utility Navigation */}
          <div>
            <h3 className="px-3 text-xs font-semibold text-secondary-500 uppercase tracking-wider mb-3">
              System
            </h3>
            {utilityNav.map((item) => (
              <NavLink
                key={item.name}
                to={item.href}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-colors',
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
          </div>
        </nav>

        {/* Pipeline Progress Indicator */}
        {currentStep >= 0 && (
          <div className="px-4 py-3 border-t border-secondary-700">
            <div className="flex items-center justify-between text-xs text-secondary-400 mb-2">
              <span>Pipeline Progress</span>
              <span>{Math.round(((currentStep + 1) / pipelineSteps.length) * 100)}%</span>
            </div>
            <div className="h-1.5 bg-secondary-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-500 rounded-full transition-all duration-300"
                style={{
                  width: `${((currentStep + 1) / pipelineSteps.length) * 100}%`,
                }}
              />
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="px-4 py-3 border-t border-secondary-700">
          <div className="text-xs text-secondary-500">
            <p>JEBI S.A.C.</p>
            <p>Version 1.0.0</p>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-14 flex items-center justify-between px-6 bg-secondary-800 border-b border-secondary-700">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-semibold text-secondary-100">
              {getPageTitle(location.pathname)}
            </h1>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-xs text-secondary-400 bg-secondary-700 px-2 py-1 rounded">
              100% Local Processing
            </span>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-xs text-secondary-400">GPU Ready</span>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function getPageTitle(pathname: string): string {
  if (pathname === '/') return 'Pipeline Dashboard';
  if (pathname.startsWith('/datasets')) return 'Step 1: Import SVO2 Files';
  if (pathname.startsWith('/jobs')) return 'Step 2: Process & Detect';
  if (pathname.startsWith('/review')) return 'Step 3: Review & Filter';
  if (pathname.startsWith('/data')) return 'Data Explorer';
  if (pathname.startsWith('/frames')) return 'Frame Details';
  if (pathname.startsWith('/settings')) return 'Settings';
  return 'Pipeline One';
}
