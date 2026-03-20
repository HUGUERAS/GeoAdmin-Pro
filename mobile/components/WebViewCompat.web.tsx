/**
 * mobile/components/WebViewCompat.web.tsx
 * Versão web — usa <iframe srcDoc> no lugar de react-native-webview.
 * Metro resolve este arquivo automaticamente na plataforma web.
 */
import { forwardRef, useImperativeHandle, useRef } from 'react'

interface Props {
  source: { html: string }
  style?: any
  javaScriptEnabled?: boolean
  originWhitelist?: string[]
  onLoad?: () => void
}

export interface WebViewCompatHandle {
  postMessage(data: string): void
}

const WebViewCompat = forwardRef<WebViewCompatHandle, Props>(
  ({ source, style, onLoad }, ref) => {
    const iframeRef = useRef<HTMLIFrameElement>(null)

    useImperativeHandle(ref, () => ({
      postMessage: (data: string) => {
        iframeRef.current?.contentWindow?.postMessage(data, '*')
      },
    }))

    return (
      <iframe
        ref={iframeRef}
        srcDoc={source.html}
        style={{ border: 'none', width: '100%', height: '100%', ...(style ?? {}) }}
        onLoad={onLoad}
      />
    )
  }
)

WebViewCompat.displayName = 'WebViewCompat'
export default WebViewCompat
