/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Override źródła changes.json (dev/staging). Domyślnie HF CDN. */
  readonly VITE_CHANGES_URL?: string
}
