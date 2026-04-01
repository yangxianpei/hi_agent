import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import 'antd/dist/reset.css'
import './index.css'
import App from './App.jsx'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import VideoParse from './pages/VideoParse.jsx'
import { ConfigProvider } from 'antd';
import EditorPage from './pages/components/EditorPage.jsx'

createRoot(document.getElementById('root')).render(
        <ConfigProvider
            theme={{
                // 全局 Seed Token（影响全局）
                token: {
                    colorPrimary: '#1890ff', // 主色
                    colorSuccess: '#52c41a', // 成功色
                    colorWarning: '#faad14', // 警告色
                    colorError: '#f5222d',   // 错误色
                    borderRadius: 4,         // 圆角
                    fontSize: 14,            // 字体大小
                },
            }}>
            <BrowserRouter>
                <Routes>
                    <Route path="/" element={<App />} />
                    <Route path="/history" element={<VideoParse initialView="history" key="history" />} />
                    <Route path="/md/:taskId" element={<EditorPage />} />
                    <Route path="/video_parse" element={<VideoParse />} />
                    <Route path="/processing/:taskId" element={<VideoParse initialView="processing" />} key="processing" />
                </Routes>
            </BrowserRouter>
        </ConfigProvider>,
)
