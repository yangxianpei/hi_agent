import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { Button, message } from 'antd'
import { Loader2, CheckCircle, XCircle } from 'lucide-react'
import { useParams, useNavigate } from 'react-router-dom'

const PROCESSING_STAGES = [
    { key: 'uploading', label: '上传视频', icon: '📤', status: true },
    { key: 'asr_started', label: '提取音频', icon: '🎵', status: false },
    { key: 'asr_done', label: '语音识别', icon: '🎙️', status: false },
    { key: 'origin_md_done', label: '生成大纲', icon: '📝', status: false },
    { key: 'ai_started', label: 'VLM 分析', icon: '🤖', status: false },
    { key: 'video_cut_done', label: '提取关键帧', icon: '🖼️', status: false },
    { key: 'ai_done', label: '生成报告', icon: '📄', status: false },
    { key: 'finished', label: '完成', icon: '✅', status: false }
]

function ProcessingStatus() {
    const esRef = useRef(null)
    const navigate = useNavigate()
    const { taskId } = useParams();
    const [reportListData, setReportListData] = useState([...JSON.parse(JSON.stringify(PROCESSING_STAGES))])
    const [status, setStatus] = useState({
        stage: 'uploading',
        progress: 0,
        message: '正在处理...',
        error: null
    })
    useEffect(() => {
        get_vedio_status(taskId)
        return () => {
            esRef.current?.close()
        }
    }, [])


    const get_vedio_status = async (task_key) => {
        try {
            const es = new EventSource(`/api/v1/video/tasks/${encodeURIComponent(task_key)}/events`);
            es.onmessage = (e) => {
                if (e.data === '[DONE]') { es.close(); return; }


                const ev = JSON.parse(e.data);
                if (ev.stage == 'not_found') {
                    es.close();
                    message.info('文件未找到，服务器已经删除了')
                    return;
                }
                const index = reportListData.findIndex(item => item.key == ev.stage)
                if (index > -1) {
                    reportListData[index].status = true
                    let n = 0
                    reportListData.forEach(i => {
                        if (i.status) {
                            n++
                        }
                    })
                    const flag = n == reportListData.length
                    setStatus({
                        stage: flag ? 'completed' : 'uploading',
                        progress: (n / reportListData.length) * 100,
                        message: flag ? '处理完成' : '正在处理...',
                        error: null
                    })
                    setReportListData([...reportListData])
                }

            };
            esRef.current = es
        } catch {
            setStatus({
                stage: 'error',
                progress: 0,
                message: err.message || '获取状态失败',
                error: err.message
            })
        }

    }










    const isError = status.stage === 'error'
    const isCompleted = status.stage === 'completed'

    return (
        <div className="max-w-4xl mx-auto">
            {/* 状态卡片 */}
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-white rounded-2xl shadow-xl p-8"
            >
                {/* 头部 */}
                <div className="text-center mb-8">
                    {isError ? (
                        <>
                            <XCircle className="w-20 h-20 text-red-500 mx-auto mb-4" />
                            <h2 className="text-2xl font-bold text-gray-800 mb-2">处理失败</h2>
                            <p className="text-red-600">{status.error}</p>
                        </>
                    ) : isCompleted ? (
                        <>
                            <CheckCircle className="w-20 h-20 text-green-500 mx-auto mb-4" />
                            <h2 className="text-2xl font-bold text-gray-800 mb-2">处理完成！</h2>
                            <p className="text-gray-600">报告已生成，正在跳转...</p>
                        </>
                    ) : (
                        <>
                            <Loader2 className="w-20 h-20 text-primary-500 mx-auto mb-4 animate-spin" />
                            <h2 className="text-2xl font-bold text-gray-800 mb-2">正在处理视频</h2>
                            <p className="text-gray-600">{status.message}</p>
                        </>
                    )}
                </div>

                {/* 进度条 */}
                {!isError && !isCompleted && (
                    <div className="mb-8">
                        <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
                            <motion.div
                                className="h-full bg-gradient-to-r from-primary-500 to-purple-600"
                                initial={{ width: 0 }}
                                animate={{ width: `${status.progress}%` }}
                                transition={{ duration: 0.5 }}
                            />
                        </div>

                    </div>
                )}

                {/* 处理阶段 */}
                <div className="space-y-4">
                    {reportListData.map((stage, index) => {
                        const isCurrent = !stage.status
                        const isCompleted = stage.status


                        return (
                            <motion.div
                                key={stage.key}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: index * 0.05 }}
                                className={`flex items-center space-x-4 p-4 rounded-lg transition-all ${isCurrent
                                    ? 'bg-primary-50 border-2 border-primary-500'
                                    : isCompleted
                                        ? 'bg-green-50'
                                        : 'bg-gray-50'
                                    }`}
                            >
                                <div className="text-3xl">{stage.icon}</div>
                                <div className="flex-1">
                                    <p className={`font-semibold ${isCurrent ? 'text-primary-700' :
                                        isCompleted ? 'text-green-700' :
                                            'text-gray-500'
                                        }`}>
                                        {stage.label}
                                    </p>
                                </div>
                                <div>
                                    {isCompleted ? (
                                        <CheckCircle className="w-6 h-6 text-green-500" />
                                    ) : isCurrent ? (
                                        <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
                                    ) : (
                                        <div className="w-6 h-6 rounded-full border-2 border-gray-300" />
                                    )}
                                </div>
                            </motion.div>
                        )
                    })}
                </div>

                {/* 操作按钮 */}
                <div className="mt-8 flex justify-center">
                    {isError && (
                        <motion.button
                            onClick={onCancel}
                            className="px-6 py-3 bg-gray-600 text-white rounded-lg font-semibold hover:bg-gray-700 transition-colors"
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                        >
                            返回重试
                        </motion.button>
                    )}
                </div>

                {/* 提示信息 */}
                {!isError && !isCompleted && (
                    <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-700">
                        <p className="font-semibold mb-1">💡 处理提示</p>
                        <p>处理时间取决于视频长度和内容复杂度，请耐心等待。您可以关闭此页面，稍后在历史记录中查看结果。</p>
                    </div>
                )}
                {
                    isCompleted && <div className='w-full py-1.5 flex justify-center'>
                        <Button type="primary" size="large" onClick={() => {
                            navigate(`/md/${taskId}`)
                        }}>查看markdown</Button>
                    </div>
                }

            </motion.div>
        </div>
    )
}

export default ProcessingStatus

