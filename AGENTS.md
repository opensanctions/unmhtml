# **unmhtml - MHTML to HTML Converter Library**

This document defines the requirements and design for a Python library that converts MHTML (MIME HTML) files to standalone HTML files with embedded resources.

## **Project Goals**

- Convert MHTML files to standalone HTML files with embedded CSS and resources
- Preserve original rendered content structure for accurate display
- Standard-library Python implementation, with security-critical HTML sanitization delegated to the maintained nh3 sanitizer
- Support integration with web applications displaying archived content
- Provide comprehensive security sanitization for untrusted content

## **Technology Requirements**

- **Language:** Python 3.8+
- **Package Manager:** uv toolchain
- **Dependencies:** Python standard library (`email`, `base64`, `mimetypes`, `urllib.parse`, `html`, `re`) plus `nh3` (Python bindings to Rust ammonia, itself html5ever-based)
- **Rationale:** a maintained ammonia/html5ever sanitizer beats owning security-critical HTML parsing. `nh3` has zero transitive runtime dependencies and ships wheels for all major platforms — a conscious trade replacing the former zero-dependency rule

## **Core Functionality**

### **MHTML Processing**
- Parse MIME multipart documents with `multipart/related` or `message/rfc822` content types
- Extract main HTML document and embedded resources (CSS, images, fonts)
- Handle Content-Location headers linking resources to HTML references
- Decode base64-encoded binary resources

### **HTML Transformation**
- Convert external CSS `<link>` tags to embedded `<style>` tags
- Transform resource references (images, fonts) to data URIs
- Resolve relative and absolute resource references
- Handle URL resolution and path mapping

### **Security Sanitization**
Sanitization for safe display of untrusted content — enabled by default, configurable per feature. Built on nh3 in two passes: a structural nh3 pass before resource embedding, then a regex pass over the embedded CSS after.

- **Architecture:** pre-embed structural nh3 pass → resource embedding → post-embed CSS regex pass stripping `@import`, non-`data:` `url()`, `expression()`, `behavior:`
- **JavaScript Removal:** `<script>` and `<noscript>` dropped with their content; `on*` event handlers gone; `javascript:` and unknown URL schemes dropped — the whole attribute is dropped, never rewritten
- **Form Defusal:** form elements (`<form>`, `<input>`, `<button>`, ...) and their content survive; submission attributes (`action`, `method`, `formaction`, `enctype`, `target`, ...) are stripped
- **Meta Tag Defusal:** `http-equiv` refresh/set-cookie and `name` dns-prefetch attributes stripped; the `<meta>` element survives as an inert stub
- **data: URI Policy:** media-type filtered to passive media; `image/svg+xml` denied on `iframe`/`embed`/`object`
- **URL Scheme Allowlist:** http/https/mailto/tel/ftp/data
- **Hostile `<base href>`:** rewritten to the document's base URL when known, else dropped
- **Comment Preservation:** comments kept verbatim — accepted risk, inert in modern browsers

## **API Design**

### **Main Interface**
- `MHTMLConverter` class with configurable security options
- `convert_file(path)` method for file-based conversion
- `convert(content)` method for string-based conversion
- Boolean flags for each security feature (all enabled by default)

### **Security Options**
- `remove_javascript`: Remove scripts with their content, `on*` event handlers, and `javascript:`/unknown-scheme URLs — the whole attribute is dropped (enabled by default)
- `disable_forms`: Defuse form elements — they and their content survive, submission attributes are stripped (enabled by default)
- `remove_meta_redirects`: Defuse dangerous meta tags — refresh/set-cookie/dns-prefetch attributes stripped, inert stub remains (enabled by default)
- `sanitize_css`: Post-embed pass removing `@import`, non-`data:` `url()`, `expression()`, `behavior:` (enabled by default)

## **Key Features**

- **Resource Embedding:** All external resources converted to data URIs
- **CSS Integration:** External stylesheets embedded as inline styles
- **Security Focus:** Comprehensive sanitization options for untrusted content
- **Error Handling:** Graceful degradation for malformed MHTML files
- **Memory Efficiency:** Process large files without excessive memory usage
- **Default Safety:** All sanitization enabled by default for secure processing

## **Testing Requirements**

- Basic MHTML to HTML conversion functionality
- Resource embedding verification (CSS, images, fonts)
- Security sanitization effectiveness testing
- Error handling for malformed input
- Content preservation during sanitization
- Performance testing with typical web page sizes (1-5MB)

## **Success Criteria**

- **Functionality:** Successful conversion of MHTML to standalone HTML
- **Performance:** Efficient processing of typical web pages
- **Reliability:** Graceful handling of malformed MHTML
- **Security:** Effective sanitization for safe display of untrusted content — hostile-input handling is defense in depth for a sandboxed display context
- **Simplicity:** Clean, minimal API with clear documentation
- **Portability:** Standard-library implementation with `nh3` as the single dependency — zero transitive runtime dependencies, wheels for all major platforms

This specification provides the foundation for building a lightweight, secure MHTML to HTML converter library.