# Pinecone Migration Scripts

This directory contains all scripts needed for migrating from Railway PostgreSQL to Pinecone.

## Scripts (Run in Order):

1. `01_create_pinecone_index.py` - Creates Pinecone serverless index
2. `02_export_embeddings.py` - Exports embeddings from PostgreSQL
3. `03_upload_to_pinecone.py` - Uploads embeddings to Pinecone
4. `04_cleanup_postgres.py` - Removes embeddings from PostgreSQL (run AFTER verification)

## Before Running:

1. Install dependencies: `pip install pinecone-client tqdm`
2. Set environment variables in `.env`:
   ```bash
   DATABASE_URL=postgresql://...
   PINECONE_API_KEY=your-key-here
   ```

## See Also:

- `../PINECONE_MIGRATION_GUIDE.md` - Complete migration guide
- `../TECHNOLOGY_STACK.md` - Current architecture documentation
