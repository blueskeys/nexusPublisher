## maven发布程序
自动扫描特定目录，以及子目录，寻找pom文件和jar文件，提交到对应maven仓库

基于python`2.7`

使用方式：
```
python maven_publish.py 待提交maven包目录
```
> 注意：目前为单线程提交

### 下阶段功能
1. 多线程
2. 记录已提交，防止重复提交，提升效率