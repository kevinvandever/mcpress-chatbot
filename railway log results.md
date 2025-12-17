INFO:backend.chat_handler:    ✅ INCLUDED - Distance 0.4760 <= threshold 0.7

INFO:backend.chat_handler:  Result 15: From Idea to Print.pdf (Page N/A)

INFO:backend.chat_handler:    Distance: 0.5257, Similarity: 0.4743 (47.4%)

INFO:backend.chat_handler:    ✅ INCLUDED - Distance 0.5257 <= threshold 0.7

INFO:backend.chat_handler:  Result 16: From Idea to Print.pdf (Page N/A)

INFO:backend.chat_handler:    Distance: 0.5257, Similarity: 0.4743 (47.4%)

INFO:backend.chat_handler:    ✅ INCLUDED - Distance 0.5257 <= threshold 0.7

INFO:backend.chat_handler:  Result 17: From Idea to Print.pdf (Page N/A)

INFO:backend.chat_handler:    Distance: 0.5257, Similarity: 0.4743 (47.4%)

INFO:backend.chat_handler:    ✅ INCLUDED - Distance 0.5257 <= threshold 0.7

INFO:backend.chat_handler:  Result 18: From Idea to Print.pdf (Page N/A)

INFO:backend.chat_handler:    Distance: 0.5257, Similarity: 0.4743 (47.4%)

INFO:backend.chat_handler:    ✅ INCLUDED - Distance 0.5257 <= threshold 0.7

INFO:backend.chat_handler:  Result 19: From Idea to Print.pdf (Page N/A)

INFO:backend.chat_handler:    Distance: 0.5257, Similarity: 0.4743 (47.4%)

INFO:backend.chat_handler:    ✅ INCLUDED - Distance 0.5257 <= threshold 0.7

INFO:backend.chat_handler:  Result 20: From Idea to Print.pdf (Page N/A)

INFO:backend.chat_handler:    Distance: 0.5322, Similarity: 0.4678 (46.8%)

INFO:backend.chat_handler:    ✅ INCLUDED - Distance 0.5322 <= threshold 0.7

INFO:backend.chat_handler:  Result 21: From Idea to Print.pdf (Page N/A)

INFO:backend.chat_handler:    Distance: 0.5322, Similarity: 0.4678 (46.8%)

INFO:backend.chat_handler:    ✅ INCLUDED - Distance 0.5322 <= threshold 0.7

INFO:backend.chat_handler:  Result 22: From Idea to Print.pdf (Page N/A)

INFO:backend.chat_handler:    Distance: 0.5322, Similarity: 0.4678 (46.8%)

INFO:backend.chat_handler:    ✅ INCLUDED - Distance 0.5322 <= threshold 0.7

INFO:backend.chat_handler:  Result 23: From Idea to Print.pdf (Page N/A)

INFO:backend.chat_handler:    Distance: 0.5475, Similarity: 0.4525 (45.3%)

INFO:backend.chat_handler:    ✅ INCLUDED - Distance 0.5475 <= threshold 0.7

INFO:backend.chat_handler:  Result 24: From Idea to Print.pdf (Page N/A)

INFO:backend.chat_handler:    Distance: 0.5475, Similarity: 0.4525 (45.3%)

INFO:backend.chat_handler:    ✅ INCLUDED - Distance 0.5475 <= threshold 0.7

INFO:backend.chat_handler:  Result 25: From Idea to Print.pdf (Page N/A)

INFO:backend.chat_handler:    Distance: 0.5475, Similarity: 0.4525 (45.3%)

INFO:backend.chat_handler:    ✅ INCLUDED - Distance 0.5475 <= threshold 0.7

INFO:backend.chat_handler:  Result 26: From Idea to Print.pdf (Page N/A)

INFO:backend.chat_handler:    Distance: 0.5645, Similarity: 0.4355 (43.5%)

INFO:backend.chat_handler:    ✅ INCLUDED - Distance 0.5645 <= threshold 0.7

INFO:backend.chat_handler:  Result 27: From Idea to Print.pdf (Page N/A)

INFO:backend.chat_handler:    Distance: 0.5645, Similarity: 0.4355 (43.5%)

INFO:backend.chat_handler:    ✅ INCLUDED - Distance 0.5645 <= threshold 0.7

INFO:backend.chat_handler:  Result 28: From Idea to Print.pdf (Page N/A)

INFO:backend.chat_handler:    Distance: 0.5645, Similarity: 0.4355 (43.5%)

INFO:backend.chat_handler:    ✅ INCLUDED - Distance 0.5645 <= threshold 0.7

INFO:backend.chat_handler:  Result 29: From Idea to Print.pdf (Page N/A)

INFO:backend.chat_handler:    Distance: 0.5645, Similarity: 0.4355 (43.5%)

INFO:backend.chat_handler:    ✅ INCLUDED - Distance 0.5645 <= threshold 0.7

INFO:backend.chat_handler:  Result 30: From Idea to Print.pdf (Page N/A)

INFO:backend.chat_handler:    Distance: 0.5645, Similarity: 0.4355 (43.5%)

INFO:backend.chat_handler:    ✅ INCLUDED - Distance 0.5645 <= threshold 0.7

INFO:backend.chat_handler:✅ Final result: 12 relevant documents included (max 12)

INFO:backend.chat_handler:Step 2 Result: 12 documents passed filtering

INFO:backend.chat_handler:Step 3: Building context from relevant documents...

INFO:backend.chat_handler:Step 3 Result: Context length = 9488 characters, 2519 tokens

INFO:backend.chat_handler:Context preview: [Source: DB2 9 System Administration for z-OS (Exam 737).pdf, Page N/A]

Roger E. Sanders, author and DB2 expert.

You were so helpful in getting me started in writing

and so generous in your time and e...

INFO:backend.chat_handler:Step 4: Context found - sending document-based request to OpenAI

INFO:backend.chat_handler:Final prompt length: 9650 characters

INFO:httpx:HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"

INFO:backend.chat_handler:✅ Saved user message to DB conversation 1394d590-d8f7-4cff-b5b7-37416eab67b5

INFO:backend.chat_handler:✅ Saved assistant message to DB conversation 1394d590-d8f7-4cff-b5b7-37416eab67b5

INFO:backend.chat_handler:About to enrich metadata for: DB2 9 System Administration for z-OS (Exam 737).pdf

INFO:backend.chat_handler:Enriching metadata for filename: DB2 9 System Administration for z-OS (Exam 737).pdf

INFO:backend.chat_handler:Found book: DB2 9 System Administration for z-OS (Exam 737) by Lakshman

ERROR:backend.chat_handler:Error enriching source metadata for DB2 9 System Administration for z-OS (Exam 737).pdf: column da.document_id does not exist

ERROR:backend.chat_handler:Traceback: Traceback (most recent call last):

  File "/app/backend/chat_handler.py", line 491, in _enrich_source_metadata

​    authors = await conn.fetch("""

​              ^^^^^^^^^^^^^^^^^^^^

  File "/app/.venv/lib/python3.11/site-packages/asyncpg/connection.py", line 694, in fetch

​    return await self._execute(

​           ^^^^^^^^^^^^^^^^^^^^

  File "/app/.venv/lib/python3.11/site-packages/asyncpg/connection.py", line 1873, in _execute

​    result, _ = await self.__execute(

​                ^^^^^^^^^^^^^^^^^^^^^

  File "/app/.venv/lib/python3.11/site-packages/asyncpg/connection.py", line 1970, in __execute

​    result, stmt = await self._do_execute(

​                   ^^^^^^^^^^^^^^^^^^^^^^^

  File "/app/.venv/lib/python3.11/site-packages/asyncpg/connection.py", line 2013, in _do_execute

​    stmt = await self._get_statement(

​           ^^^^^^^^^^^^^^^^^^^^^^^^^^

  File "/app/.venv/lib/python3.11/site-packages/asyncpg/connection.py", line 443, in _get_statement

​    statement = await self._protocol.prepare(

​                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

  File "asyncpg/protocol/protocol.pyx", line 165, in prepare

asyncpg.exceptions.UndefinedColumnError: column da.document_id does not exist

INFO:backend.chat_handler:Enrichment result: {}

INFO:backend.chat_handler:About to enrich metadata for: From Idea to Print.pdf

INFO:backend.chat_handler:Enriching metadata for filename: From Idea to Print.pdf

INFO:backend.chat_handler:Found book: From Idea to Print by Test Author

ERROR:backend.chat_handler:Error enriching source metadata for From Idea to Print.pdf: column da.document_id does not exist

ERROR:backend.chat_handler:Traceback: Traceback (most recent call last):

  File "/app/backend/chat_handler.py", line 491, in _enrich_source_metadata

​    authors = await conn.fetch("""

​              ^^^^^^^^^^^^^^^^^^^^

  File "/app/.venv/lib/python3.11/site-packages/asyncpg/connection.py", line 694, in fetch

​    return await self._execute(

​           ^^^^^^^^^^^^^^^^^^^^

  File "/app/.venv/lib/python3.11/site-packages/asyncpg/connection.py", line 1873, in _execute

​    result, _ = await self.__execute(

​                ^^^^^^^^^^^^^^^^^^^^^

  File "/app/.venv/lib/python3.11/site-packages/asyncpg/connection.py", line 1970, in __execute

​    result, stmt = await self._do_execute(

​                   ^^^^^^^^^^^^^^^^^^^^^^^

  File "/app/.venv/lib/python3.11/site-packages/asyncpg/connection.py", line 2013, in _do_execute

​    stmt = await self._get_statement(

​           ^^^^^^^^^^^^^^^^^^^^^^^^^^

  File "/app/.venv/lib/python3.11/site-packages/asyncpg/connection.py", line 443, in _get_statement

​    statement = await self._protocol.prepare(

​                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

  File "asyncpg/protocol/protocol.pyx", line 165, in prepare

asyncpg.exceptions.UndefinedColumnError: column da.document_id does not exist

INFO:backend.chat_handler:Enrichment result: {}