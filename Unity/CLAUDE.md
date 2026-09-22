# Unity — C# work rules

Full conventions (EditorConfig values, XML documentation examples): Serena memory
`csharp_unity_conventions`. The project `.editorconfig` wins when present.

Summary:
- K&R braces (`csharp_new_line_before_open_brace = none`); no newline before `else`,
  `catch`, `finally`, or object-initializer members.
- Braces required on every control structure; 4-space indent, no tabs.
- Space after cast: `(int) value`.
- Trim trailing whitespace (except `.asset`), always insert final newline.
- XML doc comments render as HTML: wrap paragraphs in `<p>`, use `<br/>` for line breaks,
  prefer `<list type="bullet|number|table">` for lists. Applies to all .NET languages.
