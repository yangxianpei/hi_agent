import MarkdownPreview from '@uiw/react-markdown-preview';
import { useEffect, useState } from 'react';
import { Button, message } from 'antd'
import { useParams, useNavigate } from 'react-router-dom'
import remarkToc from 'remark-toc';
const mdContent = `# 标题
## 二级标题
- 列表项 1
- 列表项 2
\`\`\`js
console.log('代码高亮');
\`\`\`
`;

const MyComponent = () => {
    const navigate = useNavigate()
    const [ctx, setCtx] = useState('')
    const { taskId } = useParams();
    useEffect(() => {
        document.documentElement.setAttribute('data-color-mode', 'dark');
        getMdcontext()
    }, [])

    const getMdcontext = async (kind = '') => {
        let url = `/api/v1/video/tasks/${taskId}/markdown`

        if (kind) {
            url = url + `?kind=${kind}`
        }
        try {
            const temp = await fetch(url, {
                method: 'GET',
            })
            const res = await temp.json()
            setCtx(res.content)
        } catch {
            message.info('测试服务器未查到这个文档，已经删除掉了，请重新上传')
        }
    }

    return <div className='h-full flex flex-col bg-[#0D1117]'>
        <div className='flex justify-center py-2.5 gap-1.5 relative'>
            <div className='absolute left-1.5'>
                <Button onClick={() => {
                    navigate(-1)
                }}>返回</Button>
            </div>
            <Button type='primary' onClick={() => getMdcontext()}>原始文档</Button>
            <Button type='primary' onClick={() => getMdcontext('ai')}>AI文档</Button>
            <Button type='primary' onClick={() => getMdcontext('ai_video_cut')}>原始带图文档</Button>
        </div>
        <div className='flex-1 px-2.5'>
            <MarkdownPreview source={ctx} style={{ padding: 16, height: "100%" }}
                remarkPlugins={[
                    [remarkToc, {
                        heading: '目录', // 只写一个最准
                        maxDepth: 3,
                        tight: true
                    }]
                ]}
            />
        </div>

    </div>
};

export default MyComponent