import { usePWAInstall } from '../hooks/usePWAInstall';

export function InstallPrompt() {
  const { isInstallable, install, dismiss } = usePWAInstall();

  if (!isInstallable) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-96 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-4 z-50">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 dark:text-white text-sm">
            Install Natillera PWA
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Add to home screen for quick access and offline support
          </p>
        </div>
        <button
          onClick={dismiss}
          className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          aria-label="Dismiss"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div className="mt-3 flex gap-2">
        <button
          onClick={install}
          className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium py-2 px-4 rounded-md transition-colors"
        >
          Install
        </button>
        <button
          onClick={dismiss}
          className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
        >
          Not now
        </button>
      </div>
    </div>
  );
}
