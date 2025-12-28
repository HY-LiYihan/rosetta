import json

with open('concepts.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("测试 concepts.json 文件")
print("=" * 50)
print(f"概念数量: {len(data['concepts'])}")

for i, concept in enumerate(data['concepts']):
    print(f"\n概念 {i+1}: {concept['name']}")
    print(f"示例数量: {len(concept['examples'])}")
    
    # 检查前3个示例
    for j in range(min(3, len(concept['examples']))):
        example = concept['examples'][j]
        has_explanation = 'explanation' in example
        print(f"  示例 {j+1}:")
        print(f"    文本: {example['text'][:30]}...")
        print(f"    是否有 explanation: {has_explanation}")
        if has_explanation:
            print(f"    解释长度: {len(example['explanation'])} 字符")
            print(f"    解释预览: {example['explanation'][:50]}...")

print("\n" + "=" * 50)
print("测试完成: concepts.json 结构正确")
