from typing import Dict
from .parser import MHTMLParser
from .processor import HTMLProcessor
from .security import (
    remove_javascript_content,
    sanitize_css,
    remove_forms,
    remove_meta_redirects,
    is_javascript_file,
)


class MHTMLConverter:
    """
    Main converter class for converting MHTML files to standalone HTML files.

    This class provides the primary interface for converting MHTML (MIME HTML) files
    to standalone HTML files with embedded CSS and resources. It handles the entire
    conversion process including parsing, resource embedding, and error handling.

    Args:
        remove_javascript: If True, removes script tags, event handlers, and javascript: URLs
                          for security. Default is True for secure processing.
        sanitize_css: If True, removes CSS properties that can make network requests
                     (url(), @import, expression(), behavior:). Default is True for secure processing.
        remove_forms: If True, removes form elements that could submit data externally.
                     Default is True for secure processing.
        remove_meta_redirects: If True, removes dangerous meta tags like refresh and set-cookie.
                              Default is True for secure processing.

    Example:
        >>> converter = MHTMLConverter()
        >>> html_content = converter.convert_file('example.mhtml')
        >>> # Or convert with security features disabled to preserve original content
        >>> unsafe_converter = MHTMLConverter(remove_javascript=False, sanitize_css=False,
        ...                                   remove_forms=False, remove_meta_redirects=False)
        >>> html_content = unsafe_converter.convert(mhtml_string)
        >>> # Or convert with only specific security features disabled
        >>> partial_converter = MHTMLConverter(remove_forms=False)
        >>> html_content = partial_converter.convert(mhtml_string)
    """

    def __init__(
        self,
        remove_javascript: bool = True,
        sanitize_css: bool = True,
        remove_forms: bool = True,
        remove_meta_redirects: bool = True,
    ):
        """
        Initialize the MHTML converter.

        Args:
            remove_javascript: If True, removes potentially dangerous JavaScript content
                              including script tags, event handlers, and javascript: URLs.
                              Default is True for security.
            sanitize_css: If True, removes CSS properties that can make network requests
                         (url(), @import, expression(), behavior:). Default is True for security.
            remove_forms: If True, removes form elements that could submit data externally.
                         Default is True for security.
            remove_meta_redirects: If True, removes dangerous meta tags like refresh and set-cookie.
                                  Default is True for security.
        """
        self.remove_javascript = remove_javascript
        self.sanitize_css = sanitize_css
        self.remove_forms = remove_forms
        self.remove_meta_redirects = remove_meta_redirects

    def convert_file(self, mhtml_path: str) -> str:
        """
        Convert an MHTML file to a standalone HTML string.

        Args:
            mhtml_path: Path to the MHTML file to convert

        Returns:
            Standalone HTML string with embedded CSS and resources

        Raises:
            ValueError: If the file cannot be read or processed
            FileNotFoundError: If the specified file does not exist

        Example:
            >>> converter = MHTMLConverter()
            >>> html = converter.convert_file('saved_page.mhtml')
            >>> with open('output.html', 'w') as f:
            ...     f.write(html)
        """
        try:
            with open(mhtml_path, "r", encoding="utf-8") as f:
                mhtml_content = f.read()
            return self.convert(mhtml_content)
        except Exception as e:
            raise ValueError(f"Failed to read MHTML file: {e}")

    def convert(self, mhtml_content: str) -> str:
        """
        Convert MHTML content string to a standalone HTML string.

        Args:
            mhtml_content: Raw MHTML content as a string

        Returns:
            Standalone HTML string with embedded CSS and resources

        Raises:
            ValueError: If the MHTML content is malformed or cannot be processed

        Example:
            >>> with open('page.mhtml', 'r') as f:
            ...     mhtml_content = f.read()
            >>> converter = MHTMLConverter()
            >>> html = converter.convert(mhtml_content)
        """
        try:
            # Parse MHTML to extract HTML and resources
            parser = MHTMLParser(mhtml_content)
            main_html, resources = parser.parse()

            # If we got the original content back, it means the MHTML is malformed
            if main_html == mhtml_content:
                raise ValueError("No HTML content found in MHTML")

            if not main_html:
                raise ValueError("No HTML content found in MHTML")

            # Apply security sanitization BEFORE resource embedding
            # This ensures dangerous content is removed first, then safe resources are embedded
            html_content = main_html

            if self.remove_javascript:
                html_content = remove_javascript_content(html_content)

            if self.sanitize_css:
                html_content = sanitize_css(html_content)

            if self.remove_forms:
                html_content = remove_forms(html_content)

            if self.remove_meta_redirects:
                html_content = remove_meta_redirects(html_content)

            # Filter out JavaScript files from resources if requested
            if self.remove_javascript:
                filtered_resources = self._filter_javascript_resources(resources)
            else:
                filtered_resources = resources

            # Process HTML to embed CSS and convert resources
            # This happens AFTER sanitization, so legitimate resources are safely embedded
            processor = HTMLProcessor(html_content, filtered_resources)
            final_html = processor.process()

            return final_html

        except Exception as e:
            raise ValueError(f"Failed to convert MHTML: {e}")

    def _filter_javascript_resources(
        self, resources: Dict[str, bytes]
    ) -> Dict[str, bytes]:
        """
        Filter out JavaScript files from resources to prevent embedding.

        Removes JavaScript files from the resources dictionary to prevent them
        from being embedded as data URIs in the final HTML when remove_javascript=True.

        Args:
            resources: Dictionary of resource URLs to binary content

        Returns:
            Filtered resources dictionary without JavaScript files
        """
        filtered_resources = {}

        for url, content in resources.items():
            # Check if this is a JavaScript file
            if not is_javascript_file(url):
                filtered_resources[url] = content

        return filtered_resources
