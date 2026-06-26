# **unmhtml - MHTML to HTML Converter Library**

This document defines the requirements and design for a Python library that converts MHTML (MIME HTML) files to standalone HTML files with embedded resources.

## **Project Goals**

- Convert MHTML files to standalone HTML files with embedded CSS and resources
- Preserve original rendered content structure for accurate display
- Pure Python implementation using only standard library modules
- Support integration with web applications displaying archived content
- Provide comprehensive security sanitization for untrusted content

## **Technology Requirements**

- **Language:** Python 3.8+
- **Package Manager:** uv toolchain
- **Dependencies:** Python standard library only (`email`, `base64`, `mimetypes`, `urllib.parse`, `html`, `re`)
- **Zero External Dependencies** for maximum portability

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
Optional security features for safe display of untrusted content:

- **JavaScript Removal:** Script tags, event handlers, javascript: URLs
- **CSS Sanitization:** Remove url(), @import, expression(), behavior: properties
- **Form Removal:** Remove form elements that could submit data
- **Meta Tag Sanitization:** Remove meta refresh, set-cookie, dns-prefetch tags

## **API Design**

### **Main Interface**
- `MHTMLConverter` class with configurable security options
- `convert_file(path)` method for file-based conversion
- `convert(content)` method for string-based conversion
- Boolean flags for each security feature (all enabled by default)

### **Security Options**
- `remove_javascript`: Remove all JavaScript content (enabled by default)
- `sanitize_css`: Remove dangerous CSS properties (enabled by default)
- `remove_forms`: Remove form elements (enabled by default)
- `remove_meta_redirects`: Remove dangerous meta tags (enabled by default)

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
- **Security:** Effective sanitization for safe display of untrusted content
- **Simplicity:** Clean, minimal API with clear documentation
- **Portability:** Zero external dependencies, pure Python stdlib implementation

This specification provides the foundation for building a lightweight, secure MHTML to HTML converter library.