'use client'

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Button,
  Input,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
} from '@neura/ui'
import { cn } from '@/lib/utils'
import { Send, Loader2, MessageSquare, ChevronDown, ChevronUp } from 'lucide-react'
import { chatWithDocument } from '@/services/api'
import type { ChatMessage, ChunkProvenance, ChatRequest } from '@/lib/types/document'
import { toast } from 'sonner'

interface DocumentChatProps {
  documentId: string
  documentName?: string
  className?: string
}

export default function DocumentChat({ documentId, documentName, className }: DocumentChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [currentQuery, setCurrentQuery] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingMessage, setStreamingMessage] = useState('')
  const [provenance, setProvenance] = useState<ChunkProvenance[]>([])
  const [showProvenance, setShowProvenance] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Auto-scroll when messages or streaming text updates
  useEffect(() => {
    const el = messagesEndRef.current
    if (el) {
      // Debounce a bit to avoid thrashing during fast token streams
      const id = window.setTimeout(() => {
        el.scrollIntoView({ behavior: 'smooth' })
      }, 30)
      return () => window.clearTimeout(id)
    }
  }, [messages, streamingMessage])

  const limitedHistory = useMemo(() => {
    // Limit history to last 20 messages for performance
    const max = 20
    return messages.slice(-max)
  }, [messages])

  const handleSendMessage = useCallback(async () => {
    const query = currentQuery.trim()
    if (!query) {
      toast.error('Please enter a question')
      return
    }

    // Append user message optimistically
    const nextMessages: ChatMessage[] = [...messages, { role: 'user', content: query }]
    setMessages(nextMessages)
    setCurrentQuery('')
    setIsStreaming(true)
    setStreamingMessage('')
    setProvenance([])
    setError(null)

    const request: ChatRequest = {
      document_id: documentId,
      query,
      history: limitedHistory,
      max_chunks: 5,
      similarity_threshold: 0.3,
    }

    // Create a new controller per request
  // Create a controller for this request
  abortControllerRef.current = new AbortController()

    try {
      await chatWithDocument(
        request,
        (token) => setStreamingMessage((prev) => prev + token),
        (chunks) => {
          setProvenance(chunks)
          if (chunks?.length) {
            toast.message(`Found ${chunks.length} relevant chunk${chunks.length > 1 ? 's' : ''}`)
          }
        },
        () => {
          const answer = streamingMessageRef.current
          if (answer) setMessages((prev) => [...prev, { role: 'model', content: answer }])
          setStreamingMessage('')
          setIsStreaming(false)
        },
        (errMsg) => {
          setError(errMsg)
          toast.error(errMsg)
          setIsStreaming(false)
        },
        abortControllerRef.current.signal
      )
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to start chat'
      setError(msg)
      toast.error(msg)
      setIsStreaming(false)
    }
  }, [currentQuery, documentId, limitedHistory, messages])

  // Keep a ref of streamingMessage for onComplete closure
  const streamingMessageRef = useRef('')
  useEffect(() => {
    streamingMessageRef.current = streamingMessage
  }, [streamingMessage])

  const handleStopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setIsStreaming(false)
    toast.message('Streaming stopped')
  }, [])

  // Abort in-flight request on unmount or documentId change
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
        abortControllerRef.current = null
      }
    }
  }, [documentId])

  const toggleProvenance = useCallback(() => setShowProvenance((s) => !s), [])

  // Build highlighter for the current query words
  const highlightNodes = useCallback(
    (text: string) => {
      const q = currentQuery.trim()
      if (!q) return [text]
      const terms = Array.from(new Set(q.split(/\s+/).filter(Boolean)))
      if (terms.length === 0) return [text]
      // Escape regex special chars
      const escaped = terms.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
      const regex = new RegExp(`(${escaped.join('|')})`, 'gi')
      const parts = text.split(regex)
      return parts.map((part, idx) =>
        regex.test(part) ? (
          <mark
            key={idx}
            className="bg-white/10 text-text-ui px-0.5 rounded"
          >
            {part}
          </mark>
        ) : (
          <React.Fragment key={idx}>{part}</React.Fragment>
        )
      )
    },
    [currentQuery]
  )

  return (
    <Card className={cn('bg-surface-ui border-border-ui', className)}>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5" />
            {documentName ? `Chat: ${documentName}` : 'Chat with Document'}
          </CardTitle>
          <p className="text-muted-ui text-xs">Doc ID: {documentId.slice(0, 8)}…</p>
        </div>
        {isStreaming && <Badge variant="outline">Streaming…</Badge>}
      </CardHeader>

      <CardContent>
        {/* Messages area */}
        <div className="max-h-[500px] overflow-y-auto space-y-4 pb-4">
          {/* Empty state */}
          {messages.length === 0 && !isStreaming && (
            <div className="flex flex-col items-center justify-center py-8 text-muted-ui">
              <MessageSquare className="w-8 h-8 mb-2" />
              <p>Start a conversation by asking a question about this document.</p>
            </div>
          )}

          {messages.map((m, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              className={cn(
                'rounded-lg p-3 max-w-[80%] border border-border-ui',
                m.role === 'user'
                  ? 'ml-auto bg-black-ui text-text-ui text-sm'
                  : 'mr-auto bg-surface-ui text-muted-ui text-sm'
              )}
            >
              {m.content}
            </motion.div>
          ))}

          {/* Streaming message */}
          <AnimatePresence>
            {isStreaming && streamingMessage && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                transition={{ duration: 0.2 }}
                aria-live="polite"
                className="mr-auto rounded-lg p-3 max-w-[80%] bg-surface-ui border border-border-ui text-muted-ui text-sm"
              >
                {streamingMessage}
                <span className="inline-block w-2 h-4 ml-1 align-baseline bg-text-ui animate-pulse" />
              </motion.div>
            )}
          </AnimatePresence>

          <div ref={messagesEndRef} />
        </div>

        {/* Provenance panel */}
        {provenance.length > 0 && (
          <div className="mt-2 border-t border-border-ui pt-2">
            <button
              className="flex items-center gap-2 text-sm text-muted-ui hover:text-text-ui focus:outline-none"
              onClick={toggleProvenance}
              aria-expanded={showProvenance}
              aria-controls="provenance-panel"
            >
              {showProvenance ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              Source Chunks ({provenance.length})
            </button>
            <AnimatePresence>
              {showProvenance && (
                <motion.div
                  id="provenance-panel"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.25 }}
                  className="mt-2"
                >
                  {provenance.map((c) => (
                    <div key={`${c.chunk_id}-${c.chunk_index}`} className="bg-black-ui/30 border border-border-ui rounded p-3 mb-2">
                      <div className="text-xs text-muted-ui mb-1">Chunk {c.chunk_index} • {c.similarity.toFixed(2)} similarity</div>
                      <div className="text-sm text-muted-ui whitespace-pre-wrap">
                        {c.chunk_text.length > 200 
                          ? highlightNodes(`${c.chunk_text.slice(0, 200)}…`)
                          : highlightNodes(c.chunk_text)}
                      </div>
                    </div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Input area */}
        <form
          className="mt-4 pt-4 border-t border-border-ui flex items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            void handleSendMessage()
          }}
        >
          <Input
            value={currentQuery}
            onChange={(e) => setCurrentQuery(e.target.value)}
            placeholder="Ask a question about this document..."
            disabled={isStreaming}
            className="flex-1 bg-black-ui border-border-ui text-text-ui"
            aria-label="Your message"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                void handleSendMessage()
              }
            }}
          />
          <Button
            type="submit"
            disabled={isStreaming || !currentQuery.trim()}
            aria-label="Send message"
          >
            {isStreaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </Button>
        </form>

        {/* Stop button when streaming */}
        {isStreaming && (
          <div className="mt-2">
            <Button variant="outline" onClick={handleStopStreaming}>
              Stop
            </Button>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="mt-3 bg-black-ui/30 border border-border-ui rounded p-3 text-muted-ui text-sm">
            {error}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
