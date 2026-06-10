import { useEffect, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useSelector, useDispatch } from 'react-redux'
import { Collapse, Tree, Spin } from 'antd'
import { FolderFilled, FolderOpenOutlined } from '@ant-design/icons'
import { setFolders } from '../store/quizSlice'
import { quizAPI } from '../services/api'
import './SidebarFolderTree.css'

const ROOT_KEY = 'swayame-root'

function SidebarFolderTree() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const dispatch = useDispatch()
  const { folders, foldersVersion } = useSelector(s => s.quiz)

  const selectedFolderId = useMemo(() => {
    const raw = searchParams.get('folder')
    return raw ? Number(raw) : undefined
  }, [searchParams])

  useEffect(() => {
    if (folders.length === 0) {
      quizAPI.listFolders()
        .then(r => dispatch(setFolders(r.data || [])))
        .catch(() => {})
    }
  }, [])

  const treeData = useMemo(() => {
    const map = (nodes) => (nodes || []).map(n => ({
      key: String(n.id),
      title: n.name,
      icon: selectedFolderId === n.id
        ? <FolderOpenOutlined style={{ color: '#F59E0B' }} />
        : <FolderFilled style={{ color: '#F59E0B' }} />,
      children: map(n.children || []),
    }))
    return [{
      key: ROOT_KEY,
      title: 'All Activities',
      icon: <FolderOpenOutlined style={{ color: '#F59E0B' }} />,
      children: map(folders),
    }]
  }, [folders, selectedFolderId])

  const handleSelect = (keys) => {
    const key = keys[0]
    if (!key || key === ROOT_KEY) {
      setSearchParams({}, { replace: true })
    } else {
      setSearchParams({ folder: key }, { replace: true })
    }
    // Navigate to dashboard if not already there
    if (!window.location.pathname.startsWith('/dashboard')) {
      navigate('/dashboard')
    }
  }

  const collapseItems = [{
    key: 'folders',
    label: <span style={{ fontWeight: 600, fontSize: 13, color: '#374151' }}>Folders</span>,
    children: (
      <Tree
        key={folders.length}
        showIcon
        showLine={{ showLeafIcon: false }}
        treeData={treeData}
        selectedKeys={[selectedFolderId ? String(selectedFolderId) : ROOT_KEY]}
        onSelect={handleSelect}
        defaultExpandAll
        className="sidebar-folder-tree"
        style={{ background: 'transparent', fontSize: 13 }}
      />
    ),
  }]

  return (
    <div className="sidebar-folder-accordion">
      <Collapse
        defaultActiveKey={[]}
        ghost
        items={collapseItems}
        className="sidebar-folder-collapse"
      />
    </div>
  )
}

export default SidebarFolderTree
