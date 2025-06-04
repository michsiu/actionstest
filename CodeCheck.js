const fm=FileManager.local()

const mid ='29310'
const apiBaseUrl = 'https://api-get-v2.mgsearcher.com'
const imageBaseUrl = 'https://f40-1-4.g-mh.online'
const headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36','Referer':'https://m.g-mh.org/'}


testChapterUrls =["https://api-get-v2.mgsearcher.com/api/chapter/getinfo?m=29310&c=1694296","https://api-get-v2.mgsearcher.com/api/chapter/getinfo?m=29310&c=1694478","https://api-get-v2.mgsearcher.com/api/chapter/getinfo?m=29310&c=1694827"]

chaptersHtml = testChapterUrls.map(async (url,index) => {
    console.log('task '+index+' start')
    chapterImageHtml = ''
    const req = new Request(url);
    req.headers = headers;
    req.method = 'GET';
    chapterRes = await req.loadJSON();
    console.log('task '+index+' end');
    chatperTitle = chapterRes.data.info.title;
    chapterImageHtml += '<h1>' + chatperTitle + '</h1>\n'

    chatperImagesInfo = chapterRes.data.info.images.images;

    chapterImageUrls = chatperImagesInfo.map((imageInfo)=>{

      return imageInfo.url
    });
    
    console.log('task ' + index + '-' + chapterTitle + ' imageUrls: ');
    chapterImageUrls.map(async (url)=>{
          
    const reqImage = new Request(`${imageBaseUrl}${url}`);
    reqImage.headers = headers;
    reqImage.method = 'GET';

    imageRes =  await reqImage.loadImage();

    imageData = Data.fromJPEG(imageRes);
    imageBase64 = imageData.toBase64String();
    
    chapterImageHtml += '<img src="' + imageBase64 + '"\n'
      
    })
    return chapterImageHtml
});


console.log('All Chapter Tasks End')

await chaptersHtml.then((res)=>{
    
    
})
const dataPath = fileManager.documentsDirectory() + "/quanqiubingfeng.html"
fileManager.writeString(dataPath, chaptersHtml)
