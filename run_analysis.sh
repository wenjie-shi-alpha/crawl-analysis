#!/bin/bash
# 激活虚拟环境后运行分析脚本

# 激活虚拟环境
source .venv/bin/activate

# 获取输入文件（默认为最新的 structured 数据）
INPUT_FILE="${1:-academic_data/structured/medium_scale_structured_20251211_172045.json}"

# 验证文件存在
if [ ! -f "$INPUT_FILE" ]; then
    echo "❌ 错误: 文件不存在: $INPUT_FILE"
    exit 1
fi

echo "📊 开始分析..."
echo "   输入: $INPUT_FILE"
echo "   虚拟环境: $(which python)"
echo ""

# 运行脚本
python analyze_structured_results.py --input "$INPUT_FILE"

# 检查是否成功
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 分析完成！生成的图表位置:"
    ls -lh data/output/analysis/*.png 2>/dev/null | awk '{print "   " $9 " (" $5 ")"}'
else
    echo "❌ 脚本运行失败"
    exit 1
fi
