## 基于nexus仓库的批量上传工具
自动扫描特定目录，以及子目录，寻找pom文件和jar文件或者package.json，提交到对应maven|npm仓库

基于python`2.7`

### 支持的仓库类型

1. maven
2. npm

### 配置说明

配置文件为`config.ini`
```bash
[maven]
url = http://21.32.94.176:9091/repository/mining-maven/ #自建maven服务地址
repositoryId = nexus #对应maven配置文件中server的id
generatePom = false #是否在提交jar时自动生成pom文件，默认不生成
[npm]
url = http://21.32.94.176:9091/repository/mining-npm/
```
使用方式：
```bash
python nexus_publish.py [待提交maven/NPM包目录] [类型(maven|npm)]
```

例如:
```bash
python nexus_publish.py d:\maven\ maven
```

### 下阶段功能
1. 记录已提交，防止重复提交，提升效率