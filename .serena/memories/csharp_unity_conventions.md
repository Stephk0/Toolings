# C# Unity Code Conventions

## EditorConfig Settings

### General Settings
- **Indent size:** 4 spaces
- **Indent style:** spaces (no tabs)
- **Tab width:** 4
- **Insert final newline:** true
- **Trim trailing whitespace:** true (except .asset files)

### C# Specific Settings

#### Brace Style (K&R - Opening brace on same line)
```
csharp_new_line_before_open_brace = none
csharp_new_line_before_catch = false
csharp_new_line_before_else = false
csharp_new_line_before_finally = false
csharp_new_line_before_members_in_object_initializers = false
```

#### Space After Cast
```csharp
// Correct:
int x = (int) someValue;

// Incorrect:
int x = (int)someValue;
```

#### Always Use Braces (Required for all control structures)
```
csharp_prefer_braces = true:warning
csharp_braces_for_dowhile = required
csharp_braces_for_fixed = required
csharp_braces_for_for = required
csharp_braces_for_foreach = required
csharp_braces_for_ifelse = required
csharp_braces_for_lock = required
csharp_braces_for_using = required
csharp_braces_for_while = required
```

### YAML Settings
- **Indent size:** 2 spaces
- **Tab width:** 2

## XML Documentation Formatting

XML doc content is interpreted as HTML - whitespace collapses to single space.

### Formatting Tags
- `<p>...</p>` - Wrap each paragraph
- `<br/>` - Non-paragraph line breaks
- `<list type="bullet|number|table">` - Structured lists (preferred)

### List Tag Syntax
```xml
/// <list type="bullet">
///   <item><description>First item</description></item>
///   <item><description>Second item</description></item>
/// </list>
```

### Table List Syntax
```xml
/// <list type="table">
///   <listheader>
///     <term>Parameter</term>
///     <description>Description</description>
///   </listheader>
///   <item>
///     <term>value</term>
///     <description>The input value</description>
///   </item>
/// </list>
```

### Reference
- [Recommended XML documentation tags](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/xmldoc/recommended-tags)

## Code Example (Correct Style)

```csharp
/// <summary>
/// <p>Processes the input data and returns a result.</p>
/// <list type="bullet">
///   <item><description>Validates input</description></item>
///   <item><description>Transforms data</description></item>
/// </list>
/// </summary>
public void ProcessData(int value) {
    if (value > 0) {
        DoSomething();
    } else {
        DoSomethingElse();
    }
    
    for (int i = 0; i < value; i++) {
        ProcessItem(i);
    }
    
    var result = (float) value;
}
```
