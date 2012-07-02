import unittest

from core.data.context.context import ( get_context , get_contexts, HtmlText,
                                        ScriptSingleQuote, ScriptText, HtmlComment,
                                        HtmlAttrSingleQuote )


class TestContext(unittest.TestCase):
    # 
    # TODO
    #
    # 3. expression in CSS


    html = '''
    <html>
        <head>
            <style>
            STYLE_TEXT

            h1 {
                color: "STYLE_DOUBLE_QUOTE";
                color: 'STYLE_SINGLE_QUOTE';
            }

            /*
             STYLE_COMMENT
             * */

            </style>
            <script>
            var foo = '\\'SCRIPT_SINGLE_QUOTE';
            var foo2 = "SCRIPT_DOUBLE_QUOTE <b>";
            SCRIPT_TEXT
            /*

            Some SCRIPT_MULTI_COMMENT  here

            var foo2 = "SCRIPT_DOUBLE_QUOTE <b>";


            */
            // Some SCRIPT_LINE_COMMENT  here 
            </script>
        </head>
        <body>
            <h1 a='<' foo=" ssfdsf ' ATTR_DOUBLE_QUOTE">HTML_TEXT</h1>
            <TAG>123</TAG>
            <b style="='" foo='fsdfs dfATTR_SINGLE_QUOTE'>dddd</b>
            ATTR_SINGLE_QUOTE
            <i ATTR_NAME="foo">ddd</i>
            <!--
            
            Some HTML_COMMENT here
            
            -->
            <img src="ATTR_DOUBLE_QUOTE" />
            <a href="ATTR_DOUBLE_QUOTE" />link</a>
            <script>
            var foo = '\\'SCRIPT_SINGLE_QUOTE <h1>HTML_TEXT';
            </script>
        </body>
    </html>
    ATTR_SINGLE_QUOTE'''


    def test_all(self):
        for context in get_contexts():
            self.assertEqual(
                    get_context(self.html, context.get_name())[0][0].get_name(), 
                    context.get_name()
                    )
    
    def test_html_inside_js(self):
            self.assertEqual(
                    get_context(self.html, HtmlText().get_name())[1][0].get_name(), 
                    ScriptSingleQuote().get_name()
                    )


    def test_payload(self):
        html = '''
        <html>
            <body>
                &added=blah111%3C1%3E<br>::::: blahPAYLOAD<br>::::: :::::
            </body>
        </html>
        '''
        self.assertTrue( isinstance( get_context(html, 'PAYLOAD')[0][0], HtmlText ) )

    def test_payload_double_script(self):
        html = '''
        <html>
            <script>foo</script>
                PAYLOAD
            <script>bar</script>
        </html>
        '''
        self.assertTrue( isinstance( get_context(html, 'PAYLOAD')[0][0], HtmlText ) )

    def test_payload_script_broken_double_open(self):
        html = '''
        <html>
            <script>foo
                PAYLOAD
            <script>bar</script>
        </html>
        '''
        self.assertTrue( isinstance( get_context(html, 'PAYLOAD')[0][0], ScriptText ) )

    def test_payload_script_broken_double_close(self):
        html = '''
        <html>
            <script>foo</script>
                PAYLOAD
            </script>
        </html>
        '''
        self.assertTrue( isinstance( get_context(html, 'PAYLOAD')[0][0], HtmlText ) )

    def test_payload_html_inside_comment(self):
        html = '''
        <html>
            <!-- <body>PAYLOAD</body> -->
        </html>
        '''
        self.assertTrue( isinstance( get_context(html, 'PAYLOAD')[0][0], HtmlComment ) )

    def test_payload_html_inside_script_with_comment(self):
        html = '''
        <html>
            <script>
                <!-- <body>PAYLOAD</body> -->
            </script>
        </html>
        '''
        self.assertTrue( isinstance( get_context(html, 'PAYLOAD')[0][0], ScriptText ) )

    def test_payload_script_single_quote(self):
        html = '''
        <html>
            <a foo='PAYLOAD'>
                bar
            </a>
        </html>
        '''
        self.assertTrue( isinstance( get_context(html, 'PAYLOAD')[0][0], HtmlAttrSingleQuote ) )

    def test_payload_script_single_quote(self):
        html = '''
        <html>
            <script foo='PAYLOAD'>
                bar
            </script>
        </html>
        '''
        self.assertTrue( isinstance( get_context(html, 'PAYLOAD')[0][0], HtmlAttrSingleQuote ) )

    def test_payload_text_can_break(self):
        html = '''
        <html>
            <a>PAYLOAD<</a>
        </html>
        '''
        context = get_context(html, 'PAYLOAD<')[0][0]
        self.assertTrue( context.can_break('PAYLOAD<') )

    def test_payload_src(self):
        html = '''
        <html>
            <img src="PAYLOAD" />
        </html>
        '''
        context = get_context(html, 'PAYLOAD')[0][0]
        self.assertTrue(context.is_executable())

    def test_payload_href(self):
        html = '''
        <html>
            <a href="PAYLOAD">foo</a>
        </html>
        '''
        context = get_context(html, 'PAYLOAD')[0][0]
        self.assertTrue(context.is_executable())
