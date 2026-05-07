/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// vite.config.ts 의 define 으로 빌드 시점 주입
declare const __APP_COMMIT__: string;
declare const __APP_BUILT_AT__: string;
