type InstallPromptEvent = Event & { prompt: () => Promise<void> };

let deferred: InstallPromptEvent | null = null;

export function initPwaInstallListener(onAvailable: () => void): () => void {
  const handler = (e: Event) => {
    e.preventDefault();
    deferred = e as InstallPromptEvent;
    onAvailable();
  };
  window.addEventListener("beforeinstallprompt", handler);
  return () => window.removeEventListener("beforeinstallprompt", handler);
}

export async function promptPwaInstall(): Promise<boolean> {
  if (!deferred) return false;
  await deferred.prompt();
  deferred = null;
  return true;
}

export function isStandalonePwa(): boolean {
  return window.matchMedia("(display-mode: standalone)").matches || (navigator as Navigator & { standalone?: boolean }).standalone === true;
}
