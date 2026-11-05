# product-review-agent

商品AI初审智能Agent

> AI产品落地Demo，基于Workflow编排、Skill工具封装、负样本兜底策略，实现商品资料自动化初审，**不依赖RAG向量知识库**

## ✨ 项目能力

依托现有数据清洗脚本作为流程入口，串联整套初审逻辑：

- Workflow编排：串联字段完整性校验、格式清洗、合规判断、分支流转等初审节点，形成有序审核流水线
- Skill工具封装：把独立评审逻辑封装为可复用工具，包含字段校验、关键词拦截、表格数据规整等能力
- 负样本兜底库：沉淀历史异常Case，以Few-shot方式注入提示词，辅助识别边界场景，降低大模型幻觉
- 结构化输出：统一输出风险标签、风险说明、初审结论，结果写入Excel，方便人工复核

## 🛠 技术栈

Python | Workflow流程编排 | LLM API | Skill工具封装 | Few-shot样例兜底

## 📁 目录结构

├── skills/           # 评审 Skill 工具集合

├── excel_clean.py    # 数据清洗 & 初审流程入口脚本

├── goods.xlsx        # 脱敏商品样例数据源

├── output_goods.xlsx # 初审结果输出表

├── requirements.txt  # 项目依赖

└── README.md

## 🚀 快速启动

```bash
# 安装依赖
pip install -r requirements.txt

# 执行商品初审（以excel_clean.py作为流程入口）
python excel_clean.py
```
