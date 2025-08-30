<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HTML转EPUB转换器</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/FileSaver.js/2.0.5/FileSaver.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --primary: #4361ee;
            --secondary: #3a0ca3;
            --accent: #7209b7;
            --light: #f8f9fa;
            --dark: #212529;
            --success: #4cc9f0;
            --warning: #f72585;
            --gray: #6c757d;
            --light-bg: #f1f5f9;
            --card-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
            --transition: all 0.3s ease;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, var(--light-bg) 0%, #e2e8f0 100%);
            color: var(--dark);
            line-height: 1.6;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            margin-bottom: 30px;
            padding: 30px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
            border-radius: 16px;
            box-shadow: var(--card-shadow);
            position: relative;
            overflow: hidden;
        }
        
        header::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            transform: rotate(30deg);
        }
        
        .logo {
            font-size: 2.8rem;
            font-weight: 800;
            background: linear-gradient(135deg, #fff 0%, #e0e7ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
            margin-bottom: 10px;
        }
        
        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 25px;
        }
        
        @media (max-width: 900px) {
            .main-content {
                grid-template-columns: 1fr;
            }
        }
        
        .card {
            background: white;
            border-radius: 16px;
            box-shadow: var(--card-shadow);
            padding: 25px;
            margin-bottom: 25px;
            transition: var(--transition);
            border: 1px solid rgba(255, 255, 255, 0.5);
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 30px rgba(0, 0, 0, 0.15);
        }
        
        .card-title {
            font-size: 1.5rem;
            margin-bottom: 20px;
            color: var(--secondary);
            padding-bottom: 12px;
            border-bottom: 2px solid var(--primary);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .card-title i {
            color: var(--primary);
        }
        
        input, button, select {
            width: 100%;
            padding: 14px;
            margin-bottom: 12px;
            border: none;
            border-radius: 10px;
            font-size: 1rem;
            transition: var(--transition);
        }
        
        input, select {
            background: var(--light);
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.05);
            border: 1px solid #e2e8f0;
        }
        
        input:focus, select:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(67, 97, 238, 0.2);
        }
        
        button {
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
            border: none;
            cursor: pointer;
            font-weight: 600;
            box-shadow: 0 4px 6px rgba(67, 97, 238, 0.3);
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 7px 14px rgba(67, 97, 238, 0.4);
        }
        
        button:active {
            transform: translateY(0);
        }
        
        .btn-secondary {
            background: linear-gradient(135deg, var(--success) 0%, #2a9d8f 100%);
            box-shadow: 0 4px 6px rgba(76, 201, 240, 0.3);
        }
        
        .btn-secondary:hover {
            box-shadow: 0 7px 14px rgba(76, 201, 240, 0.4);
        }
        
        .btn-cover {
            background: linear-gradient(135deg, #f72585 0%, #b5179e 100%);
            box-shadow: 0 4px 6px rgba(247, 37, 133, 0.3);
            padding: 16px;
            font-size: 1.1rem;
            margin-bottom: 15px;
        }
        
        .btn-cover:hover {
            box-shadow: 0 7px 14px rgba(247, 37, 133, 0.4);
        }
        
        .preview-container {
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 20px;
            min-height: 300px;
            max-height: 500px;
            overflow-y: auto;
            background: var(--light);
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.05);
        }
        
        .cover-preview-container {
            padding: 8px;
            margin: 15px 0;
            border: 2px dashed #cbd5e0;
            border-radius: 12px;
            background: #f8fafc;
        }
        
        .cover-preview {
            width: 200px;
            height: 280px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: center;
            background: white;
            overflow: hidden;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            border: 1px solid #e2e8f0;
        }
        
        .cover-preview img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .toc-item {
            padding: 12px 15px;
            border-bottom: 1px solid #e2e8f0;
            cursor: pointer;
            transition: var(--transition);
            border-radius: 8px;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .toc-item:before {
            content: '•';
            color: var(--primary);
            font-weight: bold;
        }
        
        .toc-item:hover {
            background-color: #f1f5f9;
            transform: translateX(5px);
        }
        
        .section-title {
            margin-top: 20px;
            margin-bottom: 12px;
            color: var(--dark);
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1.1rem;
        }
        
        .section-title i {
            color: var(--primary);
            font-size: 1.1rem;
        }
        
        .alert {
            padding: 15px 20px;
            margin: 15px 0;
            border-radius: 10px;
            font-weight: 500;
        }
        
        .alert-info {
            background-color: #e6f7ff;
            color: #1890ff;
            border-left: 4px solid #1890ff;
        }
        
        .alert-success {
            background-color: #f6ffed;
            color: #52c41a;
            border-left: 4px solid #52c41a;
        }
        
        .alert-error {
            background-color: #fff2f0;
            color: #ff4d4f;
            border-left: 4px solid #ff4d4f;
        }
        
        .alert-warning {
            background-color: #fff7e6;
            color: #fa8c16;
            border-left: 4px solid #fa8c16;
        }
        
        footer {
            text-align: center;
            margin-top: 40px;
            padding: 25px;
            color: var(--gray);
            font-size: 0.9rem;
        }
        
        .file-upload-area {
            border: 2px dashed var(--primary);
            border-radius: 12px;
            padding: 30px;
            text-align: center;
            margin-bottom: 20px;
            background: rgba(67, 97, 238, 0.03);
            cursor: pointer;
            transition: var(--transition);
            position: relative;
        }
        
        .file-upload-area.processing {
            opacity: 0.7;
            pointer-events: none;
        }
        
        .file-upload-area.processing::after {
            content: '处理中...';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(255, 255, 255, 0.9);
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: 600;
            color: var(--primary);
        }
        
        .file-upload-area:hover {
            background: rgba(67, 97, 238, 0.08);
            transform: translateY(-3px);
        }
        
        .file-upload-icon {
            font-size: 54px;
            color: var(--primary);
            margin-bottom: 15px;
        }
        
        .file-upload-text {
            font-size: 1.1rem;
            margin-bottom: 10px;
            color: var(--dark);
        }
        
        .file-upload-subtext {
            font-size: 0.9rem;
            color: var(--gray);
        }
        
        .chapter-list {
            max-height: 250px;
            overflow-y: auto;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            background: var(--light);
        }
        
        .chapter-item {
            padding: 10px 15px;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .chapter-item:last-child {
            border-bottom: none;
        }
        
        .chapter-item:before {
            content: '📖';
            font-size: 0.9rem;
        }
        
        .stats-container {
            display: flex;
            gap: 15px;
            margin-top: 15px;
        }
        
        .stat-box {
            flex: 1;
            background: var(--light);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }
        
        .stat-number {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 0.9rem;
            color: var(--gray);
        }
        
        /* 自定义滚动条 */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--primary);
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--secondary);
        }
        
        /* 优化布局 */
        .settings-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
        }
        
        .metadata-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        
        @media (max-width: 768px) {
            .metadata-grid {
                grid-template-columns: 1fr;
            }
        }
        
        .metadata-item {
            display: flex;
            flex-direction: column;
        }
        
        .metadata-item label {
            margin-bottom: 6px;
            font-weight: 600;
            color: var(--dark);
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.95rem;
        }
        
        .metadata-item label i {
            color: var(--primary);
        }
        
        .upload-section {
            text-align: center;
            padding: 20px;
            background: rgba(67, 97, 238, 0.05);
            border-radius: 12px;
            margin-bottom: 20px;
        }
        
        .divider {
            height: 1px;
            background: linear-gradient(to right, transparent, #cbd5e0, transparent);
            margin: 20px 0;
        }
        
        .splitter-container {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            margin-bottom: 20px;
            background: var(--light);
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
        }
        
        .splitter-label {
            font-weight: 600;
            color: var(--dark);
            min-width: 80px;
            font-size: 0.95rem;
        }
        
        .splitter-select {
            flex: 1;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            background: white;
            font-size: 1rem;
            text-align: center;
        }
        
        .cover-section {
            margin-top: 25px;
        }
        
        .progress-bar {
            width: 100%;
            height: 6px;
            background: #e2e8f0;
            border-radius: 3px;
            margin: 10px 0;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            border-radius: 3px;
            transition: width 0.3s ease;
        }
        
        .image-stats {
            display: flex;
            justify-content: space-between;
            font-size: 0.9rem;
            color: var(--gray);
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">
                <i class="fas fa-book"></i> EPUB生成器
            </div>
        </header>
        
        <div class="main-content">
            <div class="input-section">
                <div class="card">
                    <h2 class="card-title"><i class="fas fa-file-upload"></i> HTML文件上传</h2>
                    
                    <div class="file-upload-area" id="fileUploadArea">
                        <div class="file-upload-icon">
                            <i class="fas fa-cloud-upload-alt"></i>
                        </div>
                        <p class="file-upload-text">点击或拖放HTML文件到这里</p>
                        <p class="file-upload-subtext">支持.html和.htm格式文件</p>
                        <input type="file" id="htmlFileUpload" accept=".html,.htm" style="display: none;">
                    </div>
                    <div id="fileName" style="text-align: center; margin-bottom: 20px; font-weight: 500;"></div>
                    
                    <div id="imageProcessingInfo" style="display: none;">
                        <div class="progress-bar">
                            <div class="progress-fill" id="imageProgress" style="width: 0%"></div>
                        </div>
                        <div class="image-stats">
                            <span id="processedImages">0</span>
                            <span>/</span>
                            <span id="totalImages">0</span>
                            <span>张图片已处理</span>
                        </div>
                    </div>
                    
                    <div class="stats-container">
                        <div class="stat-box">
                            <div class="stat-number" id="chapterCount">0</div>
                            <div class="stat-label">检测到的章节</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-number" id="wordCount">0</div>
                            <div class="stat-label">预估字数</div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h2 class="card-title"><i class="fas fa-info-circle"></i> 书籍信息</h2>
                    
                    <!-- 书籍元数据栏目 -->
                    <div class="section-title">
                        <i class="fas fa-tags"></i> 书籍元数据
                    </div>
                    
                    <div class="metadata-grid">
                        <div class="metadata-item">
                            <label for="bookTitle"><i class="fas fa-heading"></i> 书名</label>
                            <input type="text" id="bookTitle" placeholder="书名">
                        </div>
                        
                        <div class="metadata-item">
                            <label for="bookAuthor"><i class="fas fa-user"></i> 作者</label>
                            <input type="text" id="bookAuthor" placeholder="作者" value="匿名作者">
                        </div>
                        
                        <div class="metadata-item">
                            <label for="bookLanguage"><i class="fas fa-language"></i> 语言</label>
                            <input type="text" id="bookLanguage" placeholder="语言" value="zh-CN">
                        </div>
                        
                        <div class="metadata-item">
                            <label for="bookPublisher"><i class="fas fa-building"></i> 出版商</label>
                            <input type="text" id="bookPublisher" placeholder="出版商" value="MicSir">
                        </div>
                    </div>
                    
                    <div class="divider"></div>
                    
                    <!-- 基本设置栏目 -->
                    <div class="section-title">
                        <i class="fas fa-cog"></i> 章节设置
                    </div>
                    
                    <div class="splitter-container">
                        <span class="splitter-label">分割方式:</span>
                        <select id="splitLevel" class="splitter-select">
                            <option value="h1" selected>按H1标题分割</option>
                            <option value="h2">按H2标题分割</option>
                            <option value="h3">按H3标题分割</option>
                        </select>
                    </div>
                </div>
                
                <!-- 单独的上传封面栏目 -->
                <div class="card">
                    <h2 class="card-title"><i class="fas fa-image"></i> 封面设置</h2>
                    
                    <div class="cover-section">
                        <input type="file" id="coverImage" accept="image/*" style="display: none;">
                        <button class="btn-cover" onclick="document.getElementById('coverImage').click()">
                            <i class="fas fa-upload"></i> 上传封面
                        </button>
                        
                        <div class="cover-preview-container">
                            <div class="cover-preview" id="coverPreview">
                                <span>封面预览</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="preview-section">
                <div class="card">
                    <h2 class="card-title"><i class="fas fa-eye"></i> 内容预览</h2>
                    <div class="preview-container" id="htmlPreview">
                        <div style="text-align: center; padding: 40px 20px; color: var(--gray);">
                            <i class="fas fa-file-alt" style="font-size: 3rem; margin-bottom: 15px;"></i>
                            <p>上传HTML文件后，这里将显示内容预览</p>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h2 class="card-title"><i class="fas fa-list-ul"></i> 检测到的章节</h2>
                    <div class="chapter-list" id="chapterList">
                        <div style="text-align: center; padding: 20px; color: var(--gray);">
                            <i class="fas fa-info-circle" style="margin-bottom: 10px;"></i>
                            <p>尚未检测到章节</p>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h2 class="card-title"><i class="fas fa-cogs"></i> 生成选项</h2>
                    <button id="previewBtn" class="btn-secondary">
                        <i class="fas fa-sync-alt"></i> 更新预览
                    </button>
                    <button id="generateBtn">
                        <i class="fas fa-download"></i> 生成EPUB文件
                    </button>
                    <div class="alert alert-info" id="messageArea">
                        <i class="fas fa-info-circle"></i> 准备就绪，请上传HTML文件生成EPUB。
                    </div>
                </div>
            </div>
        </div>
        
        <footer>
            <p>HTML to EPUB 转换器 &copy; 2023 | 基于JSZip技术</p>
        </footer>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const htmlPreview = document.getElementById('htmlPreview');
            const coverImage = document.getElementById('coverImage');
            const coverPreview = document.getElementById('coverPreview');
            const previewBtn = document.getElementById('previewBtn');
            const generateBtn = document.getElementById('generateBtn');
            const messageArea = document.getElementById('messageArea');
            const bookTitle = document.getElementById('bookTitle');
            const bookAuthor = document.getElementById('bookAuthor');
            const bookLanguage = document.getElementById('bookLanguage');
            const bookPublisher = document.getElementById('bookPublisher');
            const splitLevel = document.getElementById('splitLevel');
            const htmlFileUpload = document.getElementById('htmlFileUpload');
            const fileUploadArea = document.getElementById('fileUploadArea');
            const fileName = document.getElementById('fileName');
            const chapterList = document.getElementById('chapterList');
            const chapterCount = document.getElementById('chapterCount');
            const wordCount = document.getElementById('wordCount');
            const imageProcessingInfo = document.getElementById('imageProcessingInfo');
            const imageProgress = document.getElementById('imageProgress');
            const processedImages = document.getElementById('processedImages');
            const totalImages = document.getElementById('totalImages');
            
            let htmlContent = '';
            let coverImageBase64 = null;
            let coverImageType = null;
            let chapters = [];
            let currentFileName = '';
            let imageMap = {}; // 存储图片URL到文件名的映射
            
            // 文件上传区域点击事件
            fileUploadArea.addEventListener('click', function() {
                htmlFileUpload.click();
            });
            
            // 拖放功能
            fileUploadArea.addEventListener('dragover', function(e) {
                e.preventDefault();
                fileUploadArea.style.background = 'rgba(67, 97, 238, 0.12)';
                fileUploadArea.style.borderColor = '#4361ee';
            });
            
            fileUploadArea.addEventListener('dragleave', function() {
                fileUploadArea.style.background = 'rgba(67, 97, 238, 0.03)';
                fileUploadArea.style.borderColor = '#4361ee';
            });
            
            fileUploadArea.addEventListener('drop', function(e) {
                e.preventDefault();
                fileUploadArea.style.background = 'rgba(67, 97, 238, 0.03)';
                fileUploadArea.style.borderColor = '#4361ee';
                
                if (e.dataTransfer.files.length) {
                    htmlFileUpload.files = e.dataTransfer.files;
                    handleFileUpload(e.dataTransfer.files[0]);
                }
            });
            
            // 文件选择事件
            htmlFileUpload.addEventListener('change', function(e) {
                if (e.target.files.length) {
                    handleFileUpload(e.target.files[0]);
                }
            });
            
            async function handleFileUpload(file) {
                if (file.type !== 'text/html' && !file.name.endsWith('.html') && !file.name.endsWith('.htm')) {
                    showMessage('请选择HTML文件', 'error');
                    return;
                }
                
                currentFileName = file.name.replace(/\.(html|htm)$/i, '');
                fileName.textContent = `已选择: ${file.name}`;
                fileName.style.color = 'var(--primary)';
                
                // 设置默认书名（修复：使用正确的文件名）
                const fileNameWithoutExt = file.name.replace(/\.[^/.]+$/, "");
                bookTitle.value = fileNameWithoutExt;
                
                const reader = new FileReader();
                reader.onload = async function(e) {
                    htmlContent = e.target.result;
                    
                    // 处理HTML中的图片
                    showMessage('正在处理图片...', 'info');
                    fileUploadArea.classList.add('processing');
                    
                    try {
                        await processImagesInHTML(htmlContent);
                        updatePreview();
                        showMessage('HTML文件已成功加载', 'success');
                    } catch (error) {
                        showMessage('图片处理失败: ' + error.message, 'error');
                    } finally {
                        fileUploadArea.classList.remove('processing');
                    }
                };
                reader.readAsText(file);
            }
            
            // 处理HTML中的图片
            async function processImagesInHTML(htmlContent) {
                const parser = new DOMParser();
                const doc = parser.parseFromString(htmlContent, 'text/html');
                const images = doc.querySelectorAll('img');
                
                // 过滤出需要下载的外部图片
                const externalImages = Array.from(images).filter(img => {
                    return img.src && !img.src.startsWith('data:') && !img.src.startsWith('blob:');
                });
                
                if (externalImages.length === 0) {
                    return htmlContent;
                }
                
                // 显示图片处理信息
                imageProcessingInfo.style.display = 'block';
                totalImages.textContent = externalImages.length;
                processedImages.textContent = '0';
                imageProgress.style.width = '0%';
                
                // 下载所有图片
                imageMap = {};
                let processedCount = 0;
                
                for (const img of externalImages) {
                    try {
                        const imageData = await downloadImage(img.src);
                        if (imageData) {
                            const filename = `image_${Date.now()}_${Math.random().toString(36).substr(2, 9)}.${getImageExtension(imageData.type)}`;
                            imageMap[img.src] = {
                                filename: filename,
                                data: imageData.blob,
                                type: imageData.type
                            };
                            
                            // 更新进度
                            processedCount++;
                            processedImages.textContent = processedCount;
                            imageProgress.style.width = `${(processedCount / externalImages.length) * 100}%`;
                        }
                    } catch (error) {
                        console.warn('下载图片失败:', img.src, error);
                    }
                }
                
                // 替换HTML中的图片链接
                return replaceImageUrls(htmlContent, imageMap);
            }
            
            // 下载单张图片
            async function downloadImage(url) {
                try {
                    const response = await fetch(url);
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    const blob = await response.blob();
                    return {
                        originalUrl: url,
                        blob: blob,
                        type: blob.type
                    };
                } catch (error) {
                    console.error('下载图片失败:', url, error);
                    return null;
                }
            }
            
            // 获取图片扩展名
            function getImageExtension(mimeType) {
                const extensions = {
                    'image/jpeg': 'jpg',
                    'image/jpg': 'jpg',
                    'image/png': 'png',
                    'image/gif': 'gif',
                    'image/webp': 'webp',
                    'image/svg+xml': 'svg'
                };
                return extensions[mimeType] || 'bin';
            }
            
            // 替换HTML中的图片链接
            function replaceImageUrls(htmlContent, imageMap) {
                const parser = new DOMParser();
                const doc = parser.parseFromString(htmlContent, 'text/html');
                const images = doc.querySelectorAll('img');
                
                images.forEach(img => {
                    if (imageMap[img.src]) {
                        img.src = `images/${imageMap[img.src].filename}`;
                    }
                });
                
                return doc.documentElement.outerHTML;
            }
            
            // 更新预览
            function updatePreview() {
                if (!htmlContent) {
                    showMessage('请先上传HTML文件', 'error');
                    return;
                }
                
                htmlPreview.innerHTML = htmlContent;
                extractChapters();
                
                // 更新统计信息
                const textContent = htmlContent.replace(/<[^>]*>/g, '');
                const words = textContent.trim().split(/\s+/).length;
                wordCount.textContent = words.toLocaleString();
            }
            
            // 提取章节
            function extractChapters() {
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = htmlContent;
                const level = splitLevel.value;
                const headings = tempDiv.querySelectorAll(level);
                
                chapters = [];
                chapterList.innerHTML = '';
                
                if (headings.length === 0) {
                    chapterList.innerHTML = `
                        <div style="text-align: center; padding: 20px; color: var(--gray);">
                            <i class="fas fa-exclamation-triangle" style="margin-bottom: 10px;"></i>
                            <p>未检测到${level.toUpperCase()}标题元素，将创建单章节电子书</p>
                        </div>
                    `;
                    chapters.push({
                        title: '全部内容',
                        content: htmlContent
                    });
                    chapterCount.textContent = '1';
                    return;
                }
                
                // 获取所有内容
                const allContent = tempDiv.innerHTML;
                
                // 分割内容为章节
                let lastIndex = 0;
                headings.forEach((heading, index) => {
                    const headingText = heading.outerHTML;
                    const startPos = allContent.indexOf(headingText, lastIndex);
                    
                    if (startPos !== -1) {
                        if (index > 0) {
                            // 上一个章节的内容
                            const previousContent = allContent.substring(lastIndex, startPos);
                            chapters[chapters.length - 1].content = previousContent;
                        }
                        
                        // 新章节（保留标题标签及其内容）
                        chapters.push({
                            title: heading.textContent,
                            content: '' // 先初始化空内容
                        });
                        
                        lastIndex = startPos;
                    }
                });
                
                // 添加最后一个章节的内容
                if (chapters.length > 0) {
                    chapters[chapters.length - 1].content = allContent.substring(lastIndex);
                }
                
                // 显示章节列表和目录
                chapters.forEach((chapter, index) => {
                    const chapterItem = document.createElement('div');
                    chapterItem.className = 'chapter-item';
                    chapterItem.innerHTML = `<b>第${index + 1}章:</b> ${chapter.title || '未命名章节'}`;
                    chapterList.appendChild(chapterItem);
                });
                
                chapterCount.textContent = chapters.length;
            }
            
            // 生成EPUB
            async function generateEpub() {
                if (!htmlContent) {
                    showMessage('请先上传HTML文件', 'error');
                    return;
                }
                
                showMessage('正在生成EPUB，请稍候...', 'info');
                
                try {
                    // 创建EPUB的基本结构
                    const zip = new JSZip();
                    
                    // 添加mimetype文件（必须是ZIP中的第一个文件）
                    zip.file("mimetype", "application/epub+zip");
                    
                    // 创建META-INF容器
                    const metaInf = zip.folder("META-INF");
                    metaInf.file("container.xml", `<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>`);
                    
                    // 创建OEBPS文件夹
                    const oebps = zip.folder("OEBPS");
                    
                    // 添加CSS文件
                    oebps.file("styles.css", `body {
    font-family: serif;
    line-height: 1.6;
    margin: 0;
    padding: 20px;
    color: #333;
}

h1, h2, h3 {
    font-family: sans-serif;
    color: #0066aa;
}

h1 {
    text-align: center;
    border-bottom: 2px solid #0066aa;
    padding-bottom: 10px;
}

p {
    text-indent: 2em;
    margin-bottom: 16px;
}

hr {
    border: 0;
    height: 1px;
    background: #ccc;
    margin: 30px 0;
}

img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 15px auto;
}`);
                    
                    // 处理封面图片
                    if (coverImageBase64) {
                        oebps.file("cover.jpg", coverImageBase64, {base64: true});
                    }
                    
                    // 创建图片文件夹并添加图片
                    if (Object.keys(imageMap).length > 0) {
                        const imagesFolder = oebps.folder("images");
                        for (const [url, imageInfo] of Object.entries(imageMap)) {
                            imagesFolder.file(imageInfo.filename, imageInfo.data);
                        }
                    }
                    
                    // 创建章节文件
                    const manifestItems = [];
                    const spineItems = [];
                    const tocItems = [];
                    
                    // 生成UUID
                    const uuid = generateUUID();
                    
                    chapters.forEach((chapter, index) => {
                        const filename = `chapter${index + 1}.xhtml`;
                        
                        // 创建章节HTML文件，在每章末尾添加<hr>分割线
                        const chapterContent = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>${chapter.title || `第${index + 1}章`}</title>
    <link rel="stylesheet" type="text/css" href="styles.css"/>
</head>
<body>
    ${chapter.content}
    <hr/>
</body>
</html>`;
                        
                        oebps.file(filename, chapterContent);
                        
                        // 添加到manifest
                        manifestItems.push(`<item id="chapter${index + 1}" href="${filename}" media-type="application/xhtml+xml"/>`);
                        
                        // 添加到spine
                        spineItems.push(`<itemref idref="chapter${index + 1}"/>`);
                        
                        // 添加到toc
                        tocItems.push(`
        <navPoint id="navpoint-${index + 1}" playOrder="${index + 1}">
            <navLabel>
                <text>${chapter.title || `第${index + 1}章`}</text>
            </navLabel>
            <content src="${filename}"/>
        </navPoint>`);
                    });
                    
                    // 创建toc.ncx文件（NCX目录）
                    const ncxContent = `<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="${uuid}"/>
        <meta name="dtb:depth" content="2"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
    </head>
    <docTitle>
        <text>${bookTitle.value}</text>
    </docTitle>
    <navMap>
        ${tocItems.join('')}
    </navMap>
</ncx>`;
                    
                    oebps.file("toc.ncx", ncxContent);
                    
                    // 创建content.opf文件
                    const imageManifestItems = Object.values(imageMap).map(imageInfo => 
                        `<item id="image-${imageInfo.filename}" href="images/${imageInfo.filename}" media-type="${imageInfo.type}"/>`
                    ).join('\n    ');
                    
                    const opfContent = `<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="pub-id">${uuid}</dc:identifier>
    <dc:title>${bookTitle.value}</dc:title>
    <dc:creator>${bookAuthor.value}</dc:creator>
    <dc:language>${bookLanguage.value}</dc:language>
    <dc:publisher>${bookPublisher.value}</dc:publisher>
    ${coverImageBase64 ? '<meta name="cover" content="cover-image"/>' : ''}
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="styles" href="styles.css" media-type="text/css"/>
    ${coverImageBase64 ? '<item id="cover-image" href="cover.jpg" media-type="image/jpeg" properties="cover-image"/>' : ''}
    ${imageManifestItems}
    ${manifestItems.join('\n    ')}
  </manifest>
  <spine toc="ncx">
    ${spineItems.join('\n    ')}
  </spine>
</package>`;
                    
                    oebps.file("content.opf", opfContent);
                    
                    // 生成EPUB文件
                    zip.generateAsync({type: "blob"}).then(function(content) {
                        saveAs(content, `${bookTitle.value}.epub`);
                        showMessage('EPUB生成成功！', 'success');
                    });
                    
                } catch (error) {
                    showMessage(`生成EPUB时出错: ${error.message}`, 'error');
                }
            }
            
            // 更新预览
            previewBtn.addEventListener('click', updatePreview);
            
            // 封面图片预览
            coverImage.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        coverPreview.innerHTML = '';
                        const img = document.createElement('img');
                        img.src = e.target.result;
                        coverPreview.appendChild(img);
                        
                        // 保存封面图片数据
                        coverImageBase64 = e.target.result.split(',')[1];
                        coverImageType = file.type;
                    };
                    reader.readAsDataURL(file);
                }
            });
            
            // 生成EPUB
            generateBtn.addEventListener('click', generateEpub);
            
            function showMessage(message, type) {
                messageArea.textContent = message;
                messageArea.className = 'alert';
                
                switch(type) {
                    case 'success':
                        messageArea.classList.add('alert-success');
                        messageArea.innerHTML = `<i class="fas fa-check-circle"></i> ${message}`;
                        break;
                    case 'error':
                        messageArea.classList.add('alert-error');
                        messageArea.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`;
                        break;
                    case 'warning':
                        messageArea.classList.add('alert-warning');
                        messageArea.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${message}`;
                        break;
                    default:
                        messageArea.classList.add('alert-info');
                        messageArea.innerHTML = `<i class="fas fa-info-circle"></i> ${message}`;
                }
            }
            
            function generateUUID() {
                return 'urn:uuid:' + 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
                    return v.toString(16);
                });
            }
        });
    </script>
</body>
</html>