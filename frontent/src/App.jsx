import axios from 'axios'
import { useEffect, useMemo, useRef, useState } from 'react'
import { MdPreview } from 'md-editor-rt'
import 'md-editor-rt/lib/preview.css'
import './App.css'
import {
  Avatar,
  Badge,
  Button,
  Card,
  ConfigProvider,
  Divider,
  Input,
  Layout,
  List,
  Popover,
  Spin,
  Space,
  Tag,
  Typography,
} from 'antd'
import {
  AppstoreOutlined,
  CaretDownOutlined,
  CaretUpOutlined,
  CheckOutlined,
  CopyOutlined,
  PlusOutlined,
  RedoOutlined,
  SendOutlined,
  StopOutlined,
  UserOutlined,
} from '@ant-design/icons'

const { Header, Sider, Content } = Layout
const { Text, Title } = Typography

function App() {
  const createMessageId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
  const [input, setInput] = useState('')
  const [startSending, setStartSending] = useState({})
  const [sending, setSending] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const [model, setModel] = useState('qwen')
  const [modelModalOpen, setModelModalOpen] = useState(false)
  const [tool, setTool] = useState('fight')
  const [mcp, setMcp] = useState('deepseek')
  const [toolModalOpen, setToolModalOpen] = useState(false)
  const [mcpModalOpen, setMcpModalOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [copiedMessageId, setCopiedMessageId] = useState(null)
  const [streamingAssistantId, setStreamingAssistantId] = useState(null)
  const abortRef = useRef(null)

  const modelOptions = useMemo(
    () => [
      { value: 'deepseek', label: 'deepseek', icon: 'DS' },
    ],
    [],
  )
  const toolOptions = useMemo(
    () => [
      { value: 'date', label: '日期查询', icon:"🗓"  },
      { value: 'weather', label: '天气查询', icon: '☁' },

    ],
    [],
  )
  const mcpOptions = useMemo(
    () => [
      { value: 'cook', label: '菜谱推荐', icon: '🍳' },
      { value: 'amap', label: '高德地图', icon: '🧭' },
      { value: 'internet', label: '联网查询', icon: '🌐' },
    ],
    [],
  )
  const currentModelLabel =
    modelOptions.find((item) => item.value === model)?.label ?? '模型'
  const currentToolLabel = '工具'
    
  const currentMcpLabel = "MCP服务"
  const renderLoadedList = (title, options) => (
    <div style={{ width: 440 }}>
      <div
        style={{
          padding: '12px 14px',
          background: '#f8fafc',
          borderBottom: '1px solid #eef2f7',
          borderTopLeftRadius: 10,
          borderTopRightRadius: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Title level={5} style={{ margin: 0 }}>
            {title}
          </Title>
          <Tag style={{ margin: 0, borderRadius: 999, paddingInline: 8 }}>
            {options.length} 个已加载
          </Tag>
        </div>
      </div>

      <div style={{ maxHeight: 320, overflowY: 'auto', padding: 10, background: '#fff' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {options.map((opt) => (
            <div
              key={opt.value}
              style={{
                borderRadius: 10,
                padding: 10,
                border: '1px solid #eef2f7',
                background: '#fff',
              }}
            >
              <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                <div
                  style={{
                    width: 46,
                    height: 46,
                    borderRadius: 12,
                    background: '#f1f5f9',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#334155',
                    fontWeight: 700,
                    fontSize: 16,
                  }}
                >
                  {opt.icon}
                </div>
                <div style={{ flex: 1, minWidth: 0, textAlign: 'left' }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#0f172a' }}>
                    {opt.label}
                  </div>
                </div>
                <span
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    background: '#22c55e',
                    boxShadow: '0 0 0 2px rgba(34,197,94,0.2)',
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
  const toolPopupContent = renderLoadedList('已加载工具列表', toolOptions)
  const mcpPopupContent = renderLoadedList('已加载MCP服务列表', mcpOptions)
  const modelPopupContent = (
    <div style={{ width: 440 }}>
      <div
        style={{
          padding: '12px 14px',
          background: '#f8fafc',
          borderBottom: '1px solid #eef2f7',
          borderTopLeftRadius: 10,
          borderTopRightRadius: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Title level={5} style={{ margin: 0 }}>
            已加载模型列表
          </Title>
          <Tag style={{ margin: 0, borderRadius: 999, paddingInline: 8 }}>
            {modelOptions.length} 个已加载
          </Tag>
        </div>
      </div>

      <div style={{ maxHeight: 320, overflowY: 'auto', padding: 10, background: '#fff' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {modelOptions.map((opt) => {
            const selected = opt.value === model
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => {
                  setModel(opt.value)
                  setModelModalOpen(false)
                }}
                style={{
                  all: 'unset',
                  cursor: 'pointer',
                  borderRadius: 10,
                  padding: 10,
                  border: selected ? '2px solid rgba(79,141,231,0.5)' : '1px solid #eef2f7',
                  background: '#fff',
                }}
              >
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                  <div
                    style={{
                      width: 46,
                      height: 46,
                      borderRadius: 12,
                      background: '#f1f5f9',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#334155',
                      fontWeight: 700,
                      fontSize: 16,
                    }}
                  >
                    {opt.icon}
                  </div>
                  <div style={{ flex: 1, minWidth: 0, textAlign: 'left' }}>
                    <div style={{ fontSize: 18, fontWeight: 700, color: '#0f172a' }}>
                      {opt.label}
                    </div>
                  </div>
                  <span
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: '50%',
                      background: '#22c55e',
                      boxShadow: '0 0 0 2px rgba(34,197,94,0.2)',
                    }}
                  />
                </div>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )

  const hasMessages = useMemo(() => messages.length > 0, [messages.length])
  const bottomRef = useRef(null)
  const lastMessageContent = messages[messages.length - 1]?.content ?? ''

  useEffect(() => {
    // 只滚到“消息底部锚点”，并预留底部 fixed 输入框空间
    const id = requestAnimationFrame(() => {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
    })
    return () => cancelAnimationFrame(id)
  }, [messages.length, lastMessageContent, sending, startSending])

  const sendMessage = async (manualContent = null, appendUserMessage = true) => {
    const hasManualContent = typeof manualContent === 'string'
    const content = hasManualContent ? manualContent.trim() : input.trim()
    if (!content || sending) return
    setStartSending({})

    const assistantId = `assistant-${createMessageId()}`
    const mcpStatusId = `mcp-${assistantId}`
    setStreamingAssistantId(assistantId)
    setMessages((prev) => {
      const next = [...prev]
      if (appendUserMessage) {
        next.push({
          id: createMessageId(),
          role: 'user',
          content,
        })
      }
      // 占位一条 assistant，记录对应 prompt 以支持稳定“重新生成”
      next.push({ id: assistantId, role: 'assistant', content: '', prompt: content })
      return next
    })
    if (!hasManualContent) {
      setInput('')
    }
    setSending(true)

    try {
      const controller = new AbortController()
      abortRef.current = controller
      const res = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: {
          "Accept": 'text/event-stream',
          "Content-type":"application/json",
        },
        body: JSON.stringify({ text: content }),
        signal: controller.signal,
      })

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }

      if (!res.body) {
        throw new Error('响应体为空，无法读取 SSE 流')
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      let finished = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const events = buffer.split('\n\n')
        buffer = events.pop() ?? ''
        for (const event of events) {
          const lines = event
            .split('\n')
            .map((l) => l.trim())
            .filter(Boolean)

          for (const line of lines) {
            if (!line.startsWith('data:')) continue
            const dataStr = line.slice('data:'.length).trim()
            if (dataStr === '[DONE]') {
              finished = true
              break
            }
            try {
              const payload = JSON.parse(dataStr)
              // {"type":"tool_status","name":"mcp_howtocook_whatToEat","status":"start"} 开始显示工具调用中
              if (
                payload?.type === 'tool_status' 
              ){
                setMessages((prev) => {
                  if (prev.some((m) => m.id === mcpStatusId)) return prev
                  const idx = prev.findIndex((m) => m.id === assistantId)
                  const statusMsg = {
                    id: mcpStatusId,
                    role: 'mcp_calling',
                    content: '正在调用MCP工具...',
                  }
                  if (idx === -1) return [...prev, statusMsg]
                  return [...prev.slice(0, idx), statusMsg, ...prev.slice(idx)]
                })
                continue
              }

              const delta = typeof payload?.content === 'string' ? payload.content : ''
              if (delta) {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId ? { ...m, content: m.content + delta } : m,
                  ),
                )
              }

              if (payload?.type === 'done') {
                setMessages((prev) => prev.filter((m) => m.id !== mcpStatusId))
                finished = true
                break
              }
            } catch {
              // 若后端直接返回纯文本 data: xxx，这里也尽量兼容
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: m.content + dataStr }
                    : m,
                ),
              )
            }
          }

          if (finished) break
        }

        if (finished) {
          // 触发后续 onLoad 以外的读取结束
          await reader.cancel().catch(() => {})
          break
        }
      }
    } catch (error) {
      if (error?.name === 'AbortError') {
        setMessages((prev) => prev.filter((m) => m.id !== mcpStatusId))
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content: m.content ? `${m.content}\n\n（已中断）` : '（已中断）',
                }
              : m,
          ),
        )
        return
      }
      const msg = error?.message || '接口调用失败'
      setMessages((prev) => prev.filter((m) => m.id !== mcpStatusId))
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: `接口调用失败：${msg}` }
            : m,
        ),
      )
    } finally {
      setMessages((prev) => prev.filter((m) => m.id !== mcpStatusId))
      setStreamingAssistantId(null)
      abortRef.current = null
      setSending(false)
    }
  }

  const interrupt = () => {
    abortRef.current?.abort()
  }

  const onInputKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      sendMessage()
    }
  }

  const copyMessageContent = async (messageId, text) => {
    const content = String(text ?? '')
    if (!content) return
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(content)
      } else {
        const textarea = document.createElement('textarea')
        textarea.value = content
        textarea.style.position = 'fixed'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.focus()
        textarea.select()
        document.execCommand('copy')
        document.body.removeChild(textarea)
      }
      setCopiedMessageId(messageId)
      window.setTimeout(() => {
        setCopiedMessageId((prev) => (prev === messageId ? null : prev))
      }, 1200)
    } catch {
      // ignore copy errors silently
    }
  }

  const quickRecommendList = [
    { label: '菜谱推荐', icon: '🍳' },
    { label: '地图导航', icon: '🧭' },
    { label: '天气查询', icon: '🌤' },
    { label: '帮我搜索今天 OpenAI 相关新闻并附链接', icon: '🌐' },
  ]

  const applyQuickRecommend = (text) => {
    setInput(text)
  }

  const regenerateByAssistantMessage = (assistantMessageId) => {
    if (sending) return
    const target = messages.find((m) => m.id === assistantMessageId)
    if (!target) return
    const prompt = typeof target.prompt === 'string' ? target.prompt.trim() : ''
    if (prompt) {
      sendMessage(prompt, true)
      return
    }

    // 兼容旧消息：回退到“向上找最近一条用户消息”
    const idx = messages.findIndex((m) => m.id === assistantMessageId)
    if (idx <= 0) return
    for (let i = idx - 1; i >= 0; i -= 1) {
      if (messages[i].role === 'user' && messages[i].content) {
        sendMessage(messages[i].content, true)
        return
      }
    }
  }

  // 压缩过多空行，避免模型输出导致内容过于松散
  const compactMarkdown = (text) =>
    String(text ?? '')
      .replace(/\\n/g, '\n')
      .replace(/\n{3,}/g, '\n\n')

  // Markdown 渲染函数（增强版）：先处理后再丢给 MdPreview
  const parseMarkdown = (text) => {
    if (!text) return ''

    let html = compactMarkdown(text)

    // 1. 先处理代码块（避免代码块内容被误处理）
    html = html.replace(/```([\s\S]*?)```/gim, (match, code) => {
      return `<pre><code>${code}</code></pre>`
    })

    // 2. 处理标题（按从多到少的顺序）
    html = html.replace(/^#### (.*$)/gim, '<h4>$1</h4>')
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>')
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>')
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>')

    // 3. 处理嵌套列表（支持多级缩进）
    const lines = html.split('\n')
    const processedLines = lines.map((line) => {
      // 三级列表（6个空格或3个tab + -）
      if (/^      - (.*)$/.test(line) || /^\t\t\t- (.*)$/.test(line)) {
        return line
          .replace(/^      - (.*)$/, '<li-ul-3>$1</li-ul-3>')
          .replace(/^\t\t\t- (.*)$/, '<li-ul-3>$1</li-ul-3>')
      }
      // 二级列表（4个空格或2个tab + -）
      if (/^    - (.*)$/.test(line) || /^\t\t- (.*)$/.test(line)) {
        return line
          .replace(/^    - (.*)$/, '<li-ul-2>$1</li-ul-2>')
          .replace(/^\t\t- (.*)$/, '<li-ul-2>$1</li-ul-2>')
      }
      // 二级列表（2个空格或1个tab + -）
      if (/^  - (.*)$/.test(line) || /^\t- (.*)$/.test(line)) {
        return line
          .replace(/^  - (.*)$/, '<li-ul-2>$1</li-ul-2>')
          .replace(/^\t- (.*)$/, '<li-ul-2>$1</li-ul-2>')
      }
      // 一级无序列表
      if (/^- (.*)$/.test(line)) {
        return line.replace(/^- (.*)$/, '<li-ul-1>$1</li-ul-1>')
      }
      // 有序列表
      if (/^\d+\. (.*)$/.test(line)) {
        return line.replace(/^\d+\. (.*)$/, '<li-ol>$1</li-ol>')
      }
      return line
    })
    html = processedLines.join('\n')

    // 4. 处理三级列表
    html = html.replace(/(<li-ul-3>.*?<\/li-ul-3>(\n)*)+/gim, (match) => {
      const items = match.replace(/<li-ul-3>/g, '<li>').replace(/<\/li-ul-3>/g, '</li>')
      return '<ul class="list-level-3">' + items + '</ul>'
    })

    // 5. 处理二级列表
    html = html.replace(/(<li-ul-2>.*?<\/li-ul-2>(\n)*)+/gim, (match) => {
      const items = match.replace(/<li-ul-2>/g, '<li>').replace(/<\/li-ul-2>/g, '</li>')
      return '<ul class="list-level-2">' + items + '</ul>'
    })

    // 6. 处理一级无序列表
    html = html.replace(/(<li-ul-1>.*?<\/li-ul-1>(\n)*)+/gim, (match) => {
      const items = match.replace(/<li-ul-1>/g, '<li>').replace(/<\/li-ul-1>/g, '</li>')
      return '<ul class="list-level-1">' + items + '</ul>'
    })

    // 7. 处理有序列表
    html = html.replace(/(<li-ol>.*?<\/li-ol>(\n)*)+/gim, (match) => {
      const items = match.replace(/<li-ol>/g, '<li>').replace(/<\/li-ol>/g, '</li>')
      return '<ol>' + items + '</ol>'
    })

    // 8. 处理粗体（** 或 __）
    html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    html = html.replace(/__(.*?)__/gim, '<strong>$1</strong>')

    // 9. 处理斜体（* 或 _，但要避免与粗体冲突）
    html = html.replace(/(?<!\*)\*(?!\*)([^\*]+)\*(?!\*)/gim, '<em>$1</em>')
    html = html.replace(/(?<!_)_(?!_)([^_]+)_(?!_)/gim, '<em>$1</em>')

    // 10. 处理行内代码
    html = html.replace(/`([^`]+)`/gim, '<code>$1</code>')

    // 11. 处理链接 [text](url)
    html = html.replace(/\[([^\]]+)\]\(([^\)]+)\)/gim, '<a href="$2" target="_blank">$1</a>')

    // 12. 处理引用（> 开头）
    html = html.replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>')

    // 13. 处理分隔线（--- 或 ***）
    html = html.replace(/^(---|\*\*\*)$/gim, '<hr>')

    // 14. 处理换行（两个空格+换行 或 单独的换行）
    html = html.replace(/  \n/g, '<br>')
    html = html.replace(/\n\n+/g, '</p><p>')
    html = html.replace(/\n/g, '<br>')

    // 15. 包裹段落
    html = '<p>' + html + '</p>'

    // 16. 清理多余的空段落
    html = html.replace(/<p><\/p>/g, '')
    html = html.replace(/<p>(<h[1-6]>)/g, '$1')
    html = html.replace(/(<\/h[1-6]>)<\/p>/g, '$1')
    html = html.replace(/<p>(<ul>)/g, '$1')
    html = html.replace(/(<\/ul>)<\/p>/g, '$1')
    html = html.replace(/<p>(<ol>)/g, '$1')
    html = html.replace(/(<\/ol>)<\/p>/g, '$1')
    html = html.replace(/<p>(<pre>)/g, '$1')
    html = html.replace(/(<\/pre>)<\/p>/g, '$1')
    html = html.replace(/<p>(<blockquote>)/g, '$1')
    html = html.replace(/(<\/blockquote>)<\/p>/g, '$1')
    html = html.replace(/<p>(<hr>)<\/p>/g, '$1')

    return html
  }

  const getBottomSelectorStyle = (active) => ({
    width: 132,
    height: 34,
    borderRadius: 10,
    textAlign: 'left',
    paddingInline: 12,
    border: active ? '1px solid #90B4FF' : '1px solid #D9DEE8',
    background: active ? '#EEF4FF' : '#FFFFFF',
    color: active ? '#2B63D9' : '#1F2937',
    boxShadow: active ? '0 2px 8px rgba(43, 99, 217, 0.12)' : 'none',
    fontWeight: 500,
  })

  const selectorInnerStyle = {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  }

  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#4f8de7',
          borderRadius: 10,
        },
      }}
    >
      <Layout className="chat-app-shell" style={{ minHeight: '100vh', background: '#FFFFFF' }}>
        <style>{`
          @keyframes chatFadeUp {
            from { opacity: 0; transform: translateY(14px); }
            to { opacity: 1; transform: translateY(0); }
          }
          @keyframes botMotion {
            0% { transform: translateY(0px) scale(1) rotateY(0deg); }
            25% { transform: translateY(-7px) scale(1.02) rotateY(0deg); }
            50% { transform: translateY(0px) scale(1) rotateY(0deg); }
            75% { transform: translateY(-6px) scale(1.015) rotateY(0deg); }
            82% { transform: translateY(-4px) scale(1.01) rotateY(0deg); }
            88% { transform: translateY(-4px) scale(1.01) rotateY(180deg); }
            94% { transform: translateY(-4px) scale(1.01) rotateY(360deg); }
            100% { transform: translateY(0px) scale(1) rotateY(360deg); }
          }
          @keyframes botGlow {
            0% { box-shadow: 0 10px 26px rgba(59,102,222,0.22); }
            50% { box-shadow: 0 14px 34px rgba(59,102,222,0.34); }
            100% { box-shadow: 0 10px 26px rgba(59,102,222,0.22); }
          }
          .compact-md .md-editor-preview {
            padding: 0 !important;
            line-height: 1.45 !important;
          }
          .compact-md .md-editor-preview p,
          .compact-md .md-editor-preview ul,
          .compact-md .md-editor-preview ol,
          .compact-md .md-editor-preview blockquote {
            margin: 4px 0 !important;
          }
          .compact-md .md-editor-preview li {
            margin: 2px 0 !important;
          }
          .compact-md .md-editor-preview h1,
          .compact-md .md-editor-preview h2,
          .compact-md .md-editor-preview h3,
          .compact-md .md-editor-preview h4 {
            margin: 8px 0 4px !important;
            line-height: 1.3 !important;
          }
          .compact-md .md-editor-preview pre {
            margin: 6px 0 !important;
            padding: 8px 10px !important;
          }
          .compact-md .md-editor-preview hr {
            margin: 8px 0 !important;
          }
        `}</style>
        <Header
          className="chat-header"
          style={{
            height: 56,
            paddingInline: 16,
            background: '#d8e6fb',
            borderBottom: '1px solid #e2e8f0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            position: 'sticky',
            top: 0,
            zIndex: 10,
          }}
        >
          <Space size={10}>

            <Title level={5} style={{ margin: 0, color: '#3273cf' }}>
              agent-demo平台
            </Title>
          </Space>

          <Space size={10}>
            {/* <Tag color="geekblue" style={{ marginInlineEnd: 0 }}>
              aaaa
            </Tag> */}
            <Avatar style={{ background: '#fff', color: '#475569' }} icon={<UserOutlined />} />
          </Space>
        </Header>

        <Layout>

          <Content style={{ padding: 16 }} className="chat-content-wrapper">
            <div
              style={{
                width: 'min(980px, calc(100vw - 32px))',
                height: '100%',
                margin: '0 auto',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <div className="chat-content-inner" style={{ paddingInline: 8, paddingBottom: 8 }}>
                {!hasMessages ? (
                  <div
                    style={{
                      minHeight: '58vh',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      textAlign: 'center',
                      animation: 'chatFadeUp .32s ease',
                    }}
                  >
                    <div
                      style={{
                        width: 110,
                        height: 110,
                        borderRadius: 20,
                        background: '#2f7fe8',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#fff',
                        fontSize: 46,
                        marginBottom: 18,
                        boxShadow: '0 10px 26px rgba(59,102,222,0.26)',
                        animation: 'botMotion 4.8s ease-in-out infinite, botGlow 2.8s ease-in-out infinite',
                        transformStyle: 'preserve-3d',
                        willChange: 'transform, box-shadow',
                      }}
                    >
                      🤖
                    </div>
                    <Title level={1} style={{ marginBottom: 6, fontSize: 48 }}>
                      我是AI小助手，很高兴见到面试官您!
                    </Title>

                    <Space size={14} style={{ marginTop: 24 }}>
                      <Button type="primary" size="large" shape="round">
                        日常模式
                      </Button>
                    </Space>
                  </div>
                ) : (
                  <div style={{ animation: 'chatFadeUp .32s ease' }}>
                    <Space orientation ="vertical" size={8} style={{ width: '100%' }}>
                      {messages.map((message) =>
                        message.role === 'mcp_calling' ? (
                          <div key={message.id} style={{ display: 'flex', gap: 12, paddingLeft: 44 }}>
                            <Card
                              size="small"
                              styles={{
                                body: { padding: 10 },
                              }}
                              style={{
                                maxWidth: 760,
                                background: 'transparent',
                                border: 'none',
                                borderRadius: 12,
                                boxShadow: 'none',
                                color: '#475569',
                              }}
                            >
                              <Space size={8}>
                                <Spin size="small" />
                                <Text type="secondary">{message.content || '正在调用MCP工具...'}</Text>
                              </Space>
                            </Card>
                          </div>
                        ) : message.role === 'user' ? (
                          <div
                            key={message.id}
                            style={{
                              display: 'flex',
                              justifyContent: 'flex-end',
                              gap: 12,
                            }}
                          >
                            <Card
                              size="small"
                              styles={{
                                body: { padding: 8 },
                              }}
                              style={{
                                maxWidth: '70%',
                                background: '#F5F5F5',
                                color: '#1f2937',
                                borderRadius: 12,
                                boxShadow: '0 4px 10px rgba(15, 23, 42, 0.06)',
                                whiteSpace: 'pre-wrap',
                                border: '1px solid #ECECEC',
                              }}
                            >
                              <MdPreview
                                className="compact-md"
                                value={parseMarkdown(message.content)}
                                style={{ background: 'transparent', fontSize: 14, lineHeight: 1.45 }}
                              />
                            </Card>
                            <Avatar icon={<UserOutlined />} />
                          </div>
                        ) : (
                          <div key={message.id} style={{ display: 'flex', gap: 12 }}>
                            <Badge dot color="#4f8de7">
                              <Avatar style={{ background: '#2f7fe8' }}>AI</Avatar>
                            </Badge>
                            <Card
                              size="small"
                              styles={{
                                body: { padding: 10 },
                              }}
                              style={{
                                maxWidth: 760,
                                background: 'transparent',
                                border: 'none',
                                borderRadius: 12,
                                boxShadow: 'none',
                                color: '#475569',
                                whiteSpace: 'pre-wrap',
                                lineHeight: 1.6,
                              }}
                            >
                              {sending && !message.content ? (
                                <Space size={8}>
                                  <Spin size="small" />
                                  <Text type="secondary">正在查找...</Text>
                                </Space>
                              ) : (
                                <>
                                  <MdPreview
                                    className="compact-md"
                                    value={parseMarkdown(message.content)}
                                    style={{ background: 'transparent', fontSize: 14, lineHeight: 1.45 }}
                                  />
                                  {streamingAssistantId !== message.id && (
                                    <div
                                      style={{
                                        display: 'flex',
                                        justifyContent: 'flex-start',
                                        marginTop: 6,
                                        gap: 6,
                                      }}
                                    >
                                      <Button
                                        size="small"
                                        style={{
                                          background: '#F0F0F0',
                                          border: '1px solid #E5E5E5',
                                          color: '#666',
                                        }}
                                        icon={
                                          copiedMessageId === message.id ? (
                                            <CheckOutlined />
                                          ) : (
                                            <CopyOutlined />
                                          )
                                        }
                                        onClick={() => copyMessageContent(message.id, message.content)}
                                      />
                                      <Button
                                        size="small"
                                        style={{
                                          background: '#F0F0F0',
                                          border: '1px solid #E5E5E5',
                                          color: '#666',
                                        }}
                                        icon={<RedoOutlined />}
                                        onClick={() => regenerateByAssistantMessage(message.id)}
                                        disabled={sending}
                                      />
                                    </div>
                                  )}
                                  {streamingAssistantId !== message.id && (
                                    <div style={{ marginTop: 8 }}>
                                      <Text style={{ color: '#6b7280', fontSize: 13 }}>
                                        您可以问我如下这些功能
                                      </Text>
                                      <div
                                        style={{
                                          display: 'flex',
                                          flexDirection: 'row',
                                          gap: 8,
                                          marginTop: 8,
                                          flexWrap: 'wrap',
                                        }}
                                      >
                                        {quickRecommendList.map((item) => (
                                          <Button
                                            key={item.label}
                                            size="small"
                                            style={{
                                              background: '#F2F2F2',
                                              border: '1px solid #E8E8E8',
                                              color: '#374151',
                                              borderRadius: 999,
                                              textAlign: 'left',
                                              justifyContent: 'flex-start',
                                              height: 34,
                                              paddingInline: 14,
                                              width: 'fit-content',
                                              minWidth: 120,
                                              fontSize: 13,
                                            }}
                                            onClick={() => applyQuickRecommend(item.label)}
                                          >
                                            <span>{item.icon} {item.label}</span>
                                          </Button>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </>
                              )}
                            </Card>
                          </div>
                        ),
                      )}
                    </Space>
                  </div>
                )}
                <div ref={bottomRef} style={{ scrollMarginBottom: 12 }} />
              </div>

              <div style={{ width: '100%', marginTop: 8 }}>
                <div
                  className="chat-input-panel"
                  style={{
                    background: '#fff',
                    border: '1px solid rgba(95,125,241,0.55)',
                    borderRadius: 16,
                    padding: 14,
                    boxShadow: '0 10px 26px rgba(59,102,222,0.14)',
                  }}
                >
                    <Input.TextArea
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={onInputKeyDown}
                      autoSize={{ minRows: 4, maxRows: 8 }}
                      placeholder="输入消息，Enter 发送，Shift + Enter 换行..."
                    />

                    <div
                      style={{
                        marginTop: 10,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: 10,
                      }}
                    >
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        <Popover
                          trigger="click"
                          placement="topLeft"
                          open={modelModalOpen}
                          onOpenChange={setModelModalOpen}
                          content={modelPopupContent}
                          overlayStyle={{ paddingBottom: 8 }}
                        >
                          <Button
                            className="bubble-gel-btn"
                            size="small"
                            onClick={() => setModelModalOpen(true)}
                            style={getBottomSelectorStyle(modelModalOpen)}
                          >
                            <span style={selectorInnerStyle}>
                              <span>{currentModelLabel}</span>
                              {modelModalOpen ? <CaretUpOutlined /> : <CaretDownOutlined />}
                            </span>
                          </Button>
                        </Popover>
                        <Popover
                          trigger="click"
                          placement="topLeft"
                          open={toolModalOpen}
                          onOpenChange={setToolModalOpen}
                          content={toolPopupContent}
                          overlayStyle={{ paddingBottom: 8 }}
                        >
                          <Button
                            className="bubble-gel-btn"
                            size="small"
                            onClick={() => setToolModalOpen(true)}
                            style={getBottomSelectorStyle(toolModalOpen)}
                          >
                            <span style={selectorInnerStyle}>
                              <span>{currentToolLabel}</span>
                              {toolModalOpen ? <CaretUpOutlined /> : <CaretDownOutlined />}
                            </span>
                          </Button>
                        </Popover>
                        <Popover
                          trigger="click"
                          placement="topLeft"
                          open={mcpModalOpen}
                          onOpenChange={setMcpModalOpen}
                          content={mcpPopupContent}
                        >
                          <Button
                            className="bubble-gel-btn"
                            size="small"
                            onClick={() => setMcpModalOpen(true)}
                            style={getBottomSelectorStyle(mcpModalOpen)}
                          >
                            <span style={selectorInnerStyle}>
                              <span>{currentMcpLabel}</span>
                              {mcpModalOpen ? <CaretUpOutlined /> : <CaretDownOutlined />}
                            </span>
                          </Button>
                        </Popover>
                      </div>

                      {sending ? (
                        <Button
                          danger
                          type="primary"
                          icon={<StopOutlined />}
                          onClick={interrupt}
                        >
                          中断
                        </Button>
                      ) : (
                        <Button
                          type="primary"
                          icon={<SendOutlined />}
                          onClick={sendMessage}
                          disabled={!input.trim()}
                        >
                          发送
                        </Button>
                      )}
                    </div>
                </div>
              </div>
            </div>
          </Content>
        </Layout>
      </Layout>

    </ConfigProvider>
  )
}

export default App

