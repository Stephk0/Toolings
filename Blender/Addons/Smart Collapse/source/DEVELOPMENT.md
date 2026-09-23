# Smart Collapse - Blender Addon — developer notes

Implementation and maintenance notes. User docs: [README](../README.md).

## 🔧 Technical Details

### Detection Algorithm
```python
1. Get selected vertices and edges
2. Check if any edges exist in selection
3. If edges exist → Use standard collapse
4. If no edges:
   a. Check if 2 vertices share an edge
   b. If yes → Use collapse
   c. If no → Use merge at center
5. Handle any collapse failures → Fallback to merge
```

## 🤝 Contributing

Want to improve Smart Collapse? Here's how:

1. **Report Bugs:**
   - Include Blender version
   - Describe steps to reproduce
   - Provide example .blend file if possible

2. **Suggest Features:**
   - Explain the use case
   - Describe expected behavior
   - Consider edge cases

3. **Submit Improvements:**
   - Fork the code
   - Make your changes
   - Submit with clear description
