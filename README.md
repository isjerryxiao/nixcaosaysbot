# nickcaosays
What does nickcao say?

## running your own instance
```
repo deps: python python-pip python-pillow gimp noto-fonts noto-fonts-cjk noto-fonts-emoji python-jieba
pypi deps: python-telegram-bot==13.7 Whoosh==2.7.4
```  

### importing words
Generate your `nickcaosays.txt` and then run `/addword`.  
`nickcaosays.txt` is a line separated json file from which words are imported into the search database. format: `{"id": 1234, "chat": 1000000000, "text": "哈哈"}`
