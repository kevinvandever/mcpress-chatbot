"""
API endpoint for finding and merging duplicate authors.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import asyncpg

router = APIRouter()

class DuplicateAuthorGroup(BaseModel):
    canonical_name: str
    authors: List[dict]
    total_documents: int

class MergeRequest(BaseModel):
    keep_author_id: int
    merge_author_ids: List[int]
    dry_run: bool = True

async def get_db_connection():
    """Get database connection."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
    return await asyncpg.connect(database_url)

@router.get("/api/authors/duplicates")
async def find_duplicate_authors():
    """
    Find potential duplicate authors by comparing names (case-insensitive).
    Returns groups of authors that appear to be duplicates.
    """
    conn = await get_db_connection()
    try:
        # Get all authors with their document counts
        authors = await conn.fetch("""
            SELECT 
                a.id,
                a.name,
                a.site_url,
                LOWER(TRIM(a.name)) as normalized_name,
                COUNT(da.book_id) as document_count
            FROM authors a
            LEFT JOIN document_authors da ON a.id = da.author_id
            GROUP BY a.id, a.name, a.site_url
            ORDER BY LOWER(TRIM(a.name)), a.id
        """)
        
        # Group by normalized name
        groups = {}
        for author in authors:
            normalized = author['normalized_name']
            if normalized not in groups:
                groups[normalized] = []
            groups[normalized].append({
                'id': author['id'],
                'name': author['name'],
                'site_url': author['site_url'],
                'document_count': author['document_count']
            })
        
        # Filter to only groups with duplicates
        duplicates = []
        for normalized_name, author_list in groups.items():
            if len(author_list) > 1:
                # Find the best author (one with site_url, or most documents)
                best = max(author_list, key=lambda a: (
                    1 if a['site_url'] else 0,
                    a['document_count']
                ))
                duplicates.append({
                    'canonical_name': normalized_name,
                    'recommended_keep_id': best['id'],
                    'authors': author_list,
                    'total_documents': sum(a['document_count'] for a in author_list)
                })
        
        # Sort by total documents (most impactful first)
        duplicates.sort(key=lambda x: x['total_documents'], reverse=True)
        
        return {
            'total_duplicate_groups': len(duplicates),
            'duplicates': duplicates
        }
    finally:
        await conn.close()

@router.post("/api/authors/merge")
async def merge_authors(request: MergeRequest):
    """
    Merge duplicate authors into a single author record.
    
    - keep_author_id: The author ID to keep (all documents will be reassigned to this author)
    - merge_author_ids: List of author IDs to merge into the kept author
    - dry_run: If True, only show what would happen without making changes
    """
    conn = await get_db_connection()
    try:
        # Validate keep_author_id exists
        keep_author = await conn.fetchrow(
            "SELECT id, name, site_url FROM authors WHERE id = $1",
            request.keep_author_id
        )
        if not keep_author:
            raise HTTPException(status_code=404, detail=f"Author {request.keep_author_id} not found")
        
        # Validate merge_author_ids exist
        merge_authors = await conn.fetch(
            "SELECT id, name, site_url FROM authors WHERE id = ANY($1)",
            request.merge_author_ids
        )
        if len(merge_authors) != len(request.merge_author_ids):
            found_ids = {a['id'] for a in merge_authors}
            missing = set(request.merge_author_ids) - found_ids
            raise HTTPException(status_code=404, detail=f"Authors not found: {missing}")
        
        # Get documents that will be affected
        affected_docs = await conn.fetch("""
            SELECT da.book_id, da.author_id, b.filename, b.title
            FROM document_authors da
            JOIN books b ON da.book_id = b.id
            WHERE da.author_id = ANY($1)
        """, request.merge_author_ids)
        
        # Check for conflicts (documents that already have the keep_author)
        existing_docs = await conn.fetch("""
            SELECT book_id FROM document_authors WHERE author_id = $1
        """, request.keep_author_id)
        existing_book_ids = {d['book_id'] for d in existing_docs}
        
        conflicts = [d for d in affected_docs if d['book_id'] in existing_book_ids]
        to_reassign = [d for d in affected_docs if d['book_id'] not in existing_book_ids]
        
        result = {
            'keep_author': dict(keep_author),
            'merge_authors': [dict(a) for a in merge_authors],
            'documents_to_reassign': len(to_reassign),
            'conflicts_to_remove': len(conflicts),
            'dry_run': request.dry_run,
            'details': {
                'reassign': [{'book_id': d['book_id'], 'title': d['title']} for d in to_reassign],
                'conflicts': [{'book_id': d['book_id'], 'title': d['title']} for d in conflicts]
            }
        }
        
        if not request.dry_run:
            async with conn.transaction():
                # Reassign documents to keep_author
                for doc in to_reassign:
                    await conn.execute("""
                        UPDATE document_authors 
                        SET author_id = $1 
                        WHERE book_id = $2 AND author_id = $3
                    """, request.keep_author_id, doc['book_id'], doc['author_id'])
                
                # Remove conflicting associations (document already has keep_author)
                for doc in conflicts:
                    await conn.execute("""
                        DELETE FROM document_authors 
                        WHERE book_id = $1 AND author_id = $2
                    """, doc['book_id'], doc['author_id'])
                
                # Delete the merged authors
                await conn.execute(
                    "DELETE FROM authors WHERE id = ANY($1)",
                    request.merge_author_ids
                )
                
                result['status'] = 'completed'
                result['authors_deleted'] = len(request.merge_author_ids)
        else:
            result['status'] = 'dry_run'
        
        return result
    finally:
        await conn.close()

@router.get("/api/authors/helgren")
async def get_helgren_authors():
    """
    Specifically check Pete Helgren's author records.
    """
    conn = await get_db_connection()
    try:
        authors = await conn.fetch("""
            SELECT 
                a.id,
                a.name,
                a.site_url,
                COUNT(da.book_id) as document_count
            FROM authors a
            LEFT JOIN document_authors da ON a.id = da.author_id
            WHERE LOWER(a.name) LIKE '%helgren%'
            GROUP BY a.id, a.name, a.site_url
            ORDER BY a.id
        """)
        
        return {
            'authors': [dict(a) for a in authors],
            'recommendation': {
                'keep_id': next((a['id'] for a in authors if a['site_url']), authors[0]['id'] if authors else None),
                'merge_ids': [a['id'] for a in authors if not a['site_url']]
            }
        }
    finally:
        await conn.close()
