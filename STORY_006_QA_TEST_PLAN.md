# Story-006 QA Test Plan - Code File Upload

**Story**: File Upload for Code Analysis
**Tester**: Quinn (QA Agent) + Kevin
**Test Date**: October 14, 2025
**Environment**: Production (Netlify + Railway)
**Status**: Ready for Testing

---

## Test Environment URLs

- **Frontend**: https://mcpress-chatbot.netlify.app
- **Backend API**: https://mcpress-chatbot-production.up.railway.app
- **Test Page**: https://mcpress-chatbot.netlify.app/code-analysis/upload

---

## Pre-Test Checklist

- [ ] Frontend deployed to Netlify (check build status)
- [ ] Backend deployed to Railway (check deployment logs)
- [ ] Database migration executed (3 tables: code_uploads, upload_sessions, user_quotas)
- [ ] Story-006 code merged to main branch
- [ ] Review acceptance criteria in Story-006 file

---

## Test Categories

### 1. API Endpoint Testing (Backend)
### 2. File Validation Testing
### 3. Upload Flow Testing (E2E)
### 4. Quota Management Testing
### 5. Security Testing
### 6. Frontend UI/UX Testing
### 7. Cleanup & Expiration Testing
### 8. Performance Testing

---

## 1. API Endpoint Testing (Backend)

**Objective**: Verify all 11 `/api/code/*` endpoints are accessible and functional

### Test 1.1: Get System Limits
**Endpoint**: `GET /api/code/limits`

```bash
curl https://mcpress-chatbot-production.up.railway.app/api/code/limits
```

**Expected Response**:
```json
{
  "max_file_size": 10485760,
  "max_files_per_session": 10,
  "max_files_per_user_per_day": 50,
  "max_storage_per_user": 104857600,
  "allowed_extensions": [".rpg", ".rpgle", ".sqlrpgle", ".cl", ".clle", ".sql", ".txt"],
  "expiration_hours": 24
}
```

**Pass Criteria**: ✅ Returns correct limits

---

### Test 1.2: Create Upload Session
**Endpoint**: `POST /api/code/session`

```bash
curl -X POST https://mcpress-chatbot-production.up.railway.app/api/code/session \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "session_id": "uuid-string",
  "user_id": "user-id",
  "created_at": "2025-10-14T...",
  "expires_at": "2025-10-15T...",
  "total_files": 0,
  "total_size": 0,
  "status": "active"
}
```

**Pass Criteria**: ✅ Creates session with valid UUID and 24hr expiration

---

### Test 1.3: Get User Quota Status
**Endpoint**: `GET /api/code/quota`

```bash
curl https://mcpress-chatbot-production.up.railway.app/api/code/quota \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response**:
```json
{
  "user_id": "user-id",
  "daily_uploads": 0,
  "daily_storage": 0,
  "last_reset": "2025-10-14",
  "lifetime_uploads": 0,
  "limits": {
    "max_daily_files": 50,
    "max_storage": 104857600
  },
  "remaining": {
    "files": 50,
    "storage": 104857600
  }
}
```

**Pass Criteria**: ✅ Returns user quota with correct limits

---

### Test 1.4: Validate File Before Upload
**Endpoint**: `POST /api/code/validate`

```bash
curl -X POST https://mcpress-chatbot-production.up.railway.app/api/code/validate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test.rpgle",
    "file_size": 5000,
    "session_id": "session-uuid"
  }'
```

**Expected Response**:
```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

**Pass Criteria**: ✅ Valid file returns `valid: true`, invalid returns errors

---

### Test 1.5: Upload Code File
**Endpoint**: `POST /api/code/upload`

**Create test file**:
```bash
echo "DCL-S myVar CHAR(50);" > test_program.rpgle
```

**Upload**:
```bash
curl -X POST https://mcpress-chatbot-production.up.railway.app/api/code/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test_program.rpgle" \
  -F "session_id=session-uuid"
```

**Expected Response**:
```json
{
  "id": "file-uuid",
  "user_id": "user-id",
  "session_id": "session-uuid",
  "filename": "test_program.rpgle",
  "file_type": ".rpgle",
  "file_size": 25,
  "uploaded_at": "2025-10-14T...",
  "expires_at": "2025-10-15T...",
  "analyzed": false
}
```

**Pass Criteria**: ✅ File uploaded, stored in /tmp/code-uploads/, DB record created

---

### Test 1.6: List User Files
**Endpoint**: `GET /api/code/files`

```bash
curl https://mcpress-chatbot-production.up.railway.app/api/code/files \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response**:
```json
[
  {
    "id": "file-uuid",
    "filename": "test_program.rpgle",
    "file_type": ".rpgle",
    "file_size": 25,
    "uploaded_at": "2025-10-14T...",
    "expires_at": "2025-10-15T...",
    "analyzed": false
  }
]
```

**Pass Criteria**: ✅ Returns list of user's uploaded files only

---

### Test 1.7: Get File Content
**Endpoint**: `GET /api/code/file/{file_id}`

```bash
curl https://mcpress-chatbot-production.up.railway.app/api/code/file/{file-uuid} \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response**:
```json
{
  "id": "file-uuid",
  "filename": "test_program.rpgle",
  "content": "DCL-S myVar CHAR(50);"
}
```

**Pass Criteria**: ✅ Returns file content, only for file owner

---

### Test 1.8: Get File Metadata
**Endpoint**: `GET /api/code/file/{file_id}/info`

```bash
curl https://mcpress-chatbot-production.up.railway.app/api/code/file/{file-uuid}/info \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response**:
```json
{
  "id": "file-uuid",
  "filename": "test_program.rpgle",
  "file_type": ".rpgle",
  "file_size": 25,
  "uploaded_at": "2025-10-14T...",
  "expires_at": "2025-10-15T...",
  "analyzed": false
}
```

**Pass Criteria**: ✅ Returns metadata without content

---

### Test 1.9: Delete File
**Endpoint**: `DELETE /api/code/file/{file_id}`

```bash
curl -X DELETE https://mcpress-chatbot-production.up.railway.app/api/code/file/{file-uuid} \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response**:
```json
{
  "success": true,
  "message": "File deleted successfully"
}
```

**Pass Criteria**: ✅ File deleted from filesystem and DB, quota updated

---

### Test 1.10: Admin Stats (if admin user)
**Endpoint**: `GET /api/code/admin/stats`

```bash
curl https://mcpress-chatbot-production.up.railway.app/api/code/admin/stats \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

**Expected Response**:
```json
{
  "total_uploads": 1,
  "total_users": 1,
  "total_storage": 25,
  "active_sessions": 1
}
```

**Pass Criteria**: ✅ Returns system statistics (admin only)

---

### Test 1.11: Admin Manual Cleanup (if admin user)
**Endpoint**: `POST /api/code/admin/cleanup`

```bash
curl -X POST https://mcpress-chatbot-production.up.railway.app/api/code/admin/cleanup \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

**Expected Response**:
```json
{
  "files_cleaned": 0,
  "storage_freed": 0
}
```

**Pass Criteria**: ✅ Triggers cleanup, returns count of deleted files

---

## 2. File Validation Testing

### Test 2.1: Valid File Extensions
**Objective**: Verify all allowed extensions are accepted

**Test Files**:
- `test.rpg` - ✅ Should accept
- `test.rpgle` - ✅ Should accept
- `test.sqlrpgle` - ✅ Should accept
- `test.cl` - ✅ Should accept
- `test.clle` - ✅ Should accept
- `test.sql` - ✅ Should accept
- `test.txt` - ✅ Should accept

**Method**: Upload each via frontend or API

**Pass Criteria**: ✅ All 7 file types accepted

---

### Test 2.2: Invalid File Extensions
**Objective**: Verify unauthorized file types are rejected

**Test Files**:
- `test.exe` - ❌ Should reject
- `test.py` - ❌ Should reject
- `test.js` - ❌ Should reject
- `test.pdf` - ❌ Should reject
- `test.zip` - ❌ Should reject

**Expected Error**: "File type not supported. Please upload .rpg, .rpgle, .sqlrpgle, .cl, .clle, or .sql files"

**Pass Criteria**: ✅ All invalid types rejected with clear error

---

### Test 2.3: File Size Limits
**Objective**: Verify 10MB file size limit enforcement

**Test Cases**:
- Upload 1KB file - ✅ Should accept
- Upload 5MB file - ✅ Should accept
- Upload 9.9MB file - ✅ Should accept
- Upload 10.1MB file - ❌ Should reject
- Upload 20MB file - ❌ Should reject

**Create large test file**:
```bash
# Create 11MB file
dd if=/dev/zero of=large_file.rpgle bs=1m count=11
```

**Expected Error**: "File size exceeds 10MB limit. Please upload a smaller file"

**Pass Criteria**: ✅ Files ≤10MB accepted, >10MB rejected

---

### Test 2.4: Content Security Scanning
**Objective**: Verify credential detection in file content

**Test File** (`credentials.rpgle`):
```rpgle
DCL-S apiKey CHAR(50) INZS('sk_live_12345abcdef');
DCL-S password CHAR(20) INZS('MyP@ssw0rd');
DCL-S token CHAR(100) INZS('ghp_abc123xyz789');
```

**Expected Warning**: "File may contain credentials. Please remove sensitive data before uploading."

**Pass Criteria**: ✅ Warning issued for potential credentials

---

### Test 2.5: Encoding Detection
**Objective**: Verify support for UTF-8, Latin-1, EBCDIC

**Test Files**:
- UTF-8 encoded `.rpgle` - ✅ Should accept
- Latin-1 encoded `.rpgle` - ✅ Should accept
- EBCDIC encoded `.rpgle` - ✅ Should detect and convert

**Pass Criteria**: ✅ All encodings supported, EBCDIC converted to UTF-8

---

## 3. Upload Flow Testing (E2E)

### Test 3.1: Single File Upload
**Objective**: Complete upload flow for single file

**Steps**:
1. Navigate to `/code-analysis/upload`
2. Click upload zone or drag file
3. Select valid `.rpgle` file (≤10MB)
4. Verify upload progress bar appears
5. Verify success message appears
6. Verify file appears in file list
7. Verify quota indicator updates

**Expected**:
- ✅ Progress bar shows during upload
- ✅ Success message: "✓ {filename} uploaded successfully (expires in 24 hours)"
- ✅ File appears in list with correct metadata
- ✅ Quota shows "1/50 files uploaded today"

**Pass Criteria**: ✅ All steps complete without errors

---

### Test 3.2: Multiple File Upload
**Objective**: Upload 10 files simultaneously (max per session)

**Steps**:
1. Create 10 test files (.rpg, .rpgle, .cl, etc.)
2. Drag all 10 files to upload zone
3. Verify all files validate
4. Verify all progress bars update
5. Verify all success messages
6. Verify all files in file list
7. Verify quota: "10/50 files uploaded today"

**Pass Criteria**: ✅ All 10 files uploaded successfully

---

### Test 3.3: Exceed Session File Limit
**Objective**: Verify max 10 files per session enforcement

**Steps**:
1. Upload 10 files successfully
2. Attempt to upload 11th file
3. Verify error message appears

**Expected Error**: "Maximum 10 files per session. Please analyze current files first"

**Pass Criteria**: ✅ 11th file rejected with clear error

---

### Test 3.4: Drag-and-Drop Interface
**Objective**: Verify drag-drop functionality

**Steps**:
1. Drag valid file over upload zone
2. Verify visual feedback (border highlight, etc.)
3. Drop file
4. Verify upload begins
5. Verify success

**Pass Criteria**: ✅ Visual feedback works, upload succeeds

---

### Test 3.5: File Preview
**Objective**: Verify syntax-highlighted preview modal

**Steps**:
1. Upload `.rpgle` file with RPG code
2. Click "Preview" button
3. Verify modal opens
4. Verify syntax highlighting applied
5. Verify line numbers visible
6. Close modal

**Pass Criteria**: ✅ Code displayed with proper syntax highlighting

---

### Test 3.6: File Deletion
**Objective**: Verify manual file removal

**Steps**:
1. Upload test file
2. Click "Delete" button
3. Verify confirmation prompt (if any)
4. Confirm deletion
5. Verify file removed from list
6. Verify quota decremented
7. Verify file deleted from backend

**Pass Criteria**: ✅ File removed from UI, backend, and quota updated

---

## 4. Quota Management Testing

### Test 4.1: Daily Upload Limit
**Objective**: Verify 50 files/day limit per user

**Steps**:
1. Upload 50 files throughout the day (may need script)
2. Verify quota shows "50/50 files uploaded today"
3. Attempt to upload 51st file
4. Verify rejection with error

**Expected Error**: "Daily upload limit reached. Please try again tomorrow"

**Pass Criteria**: ✅ 51st file rejected, quota enforced

---

### Test 4.2: Storage Quota Limit
**Objective**: Verify 100MB storage limit per user

**Steps**:
1. Upload files totaling 99MB
2. Verify quota shows ~99MB/100MB
3. Attempt to upload 2MB file (would exceed 100MB)
4. Verify rejection

**Expected Error**: "Storage quota exceeded. Please delete some files or try tomorrow"

**Pass Criteria**: ✅ Storage limit enforced

---

### Test 4.3: Quota Reset at Midnight
**Objective**: Verify daily quota reset

**Method**: Check database function or wait for midnight

**SQL Check**:
```sql
SELECT * FROM user_quotas WHERE last_reset < CURRENT_DATE;
-- Should show quotas that need reset
```

**Expected**: Daily uploads/storage reset to 0 at midnight

**Pass Criteria**: ✅ Quotas reset after midnight (verify via SQL or next-day test)

---

### Test 4.4: Quota Display Accuracy
**Objective**: Verify quota indicator shows correct values

**Steps**:
1. Upload 5 files (10MB total)
2. Verify indicator shows:
   - "5/50 files uploaded today"
   - "10MB/100MB storage used"
3. Delete 2 files (4MB)
4. Verify indicator updates:
   - "3/50 files uploaded today"
   - "6MB/100MB storage used"

**Pass Criteria**: ✅ Quota display updates in real-time

---

## 5. Security Testing

### Test 5.1: Cross-User File Access
**Objective**: Verify users cannot access other users' files

**Steps**:
1. User A uploads file (get file_id)
2. User B attempts to access User A's file via API:
   ```bash
   curl https://mcpress-chatbot-production.up.railway.app/api/code/file/{user-a-file-id} \
     -H "Authorization: Bearer USER_B_TOKEN"
   ```
3. Verify 403 Forbidden response

**Expected Error**: "Unauthorized access to file"

**Pass Criteria**: ✅ 403 error, access denied

---

### Test 5.2: Unauthenticated Access
**Objective**: Verify authentication required for all endpoints

**Steps**:
1. Attempt to access `/api/code/files` without token
2. Attempt to upload file without token
3. Verify 401 Unauthorized response

**Pass Criteria**: ✅ All endpoints require authentication

---

### Test 5.3: Session Isolation
**Objective**: Verify session-based file isolation

**Steps**:
1. Create Session A, upload files
2. Create Session B, upload files
3. Verify files stored in separate session directories
4. Verify API returns only files for current session

**Expected Directory Structure**:
```
/tmp/code-uploads/
  /user-id/
    /session-a-id/
      /file1.rpgle
    /session-b-id/
      /file2.rpgle
```

**Pass Criteria**: ✅ Files isolated by session

---

### Test 5.4: Malicious Filename Handling
**Objective**: Verify safe handling of dangerous filenames

**Test Filenames**:
- `../../etc/passwd.rpgle` - Path traversal attempt
- `<script>alert('xss')</script>.rpgle` - XSS attempt
- `file; rm -rf /.rpgle` - Command injection attempt

**Expected**: Filenames sanitized, no security issues

**Pass Criteria**: ✅ All malicious filenames handled safely

---

### Test 5.5: File Type Spoofing
**Objective**: Verify content-based file type detection (not just extension)

**Steps**:
1. Rename `malicious.exe` to `test.rpgle`
2. Attempt to upload
3. Verify rejection based on content inspection

**Pass Criteria**: ✅ File rejected if content doesn't match extension

---

## 6. Frontend UI/UX Testing

### Test 6.1: Upload Zone Visual Feedback
**Objective**: Verify user-friendly upload interface

**Test**:
- Hover over upload zone - should show visual highlight
- Drag file over - border/background should change
- Drop file - upload should begin immediately
- Invalid file - error should display clearly

**Pass Criteria**: ✅ Clear visual feedback for all states

---

### Test 6.2: Progress Indicators
**Objective**: Verify upload progress visibility

**Test**:
- Upload 5MB file
- Verify progress bar shows percentage (0% → 100%)
- Verify spinner or loading indicator
- Verify completion notification

**Pass Criteria**: ✅ Progress clearly visible during upload

---

### Test 6.3: Error Message Display
**Objective**: Verify clear error messages

**Test Scenarios**:
- Upload invalid file type → Clear error message
- Upload oversized file → File size error
- Exceed quota → Quota error
- Network failure → Connection error

**Expected**: All errors displayed in red Alert component with clear text

**Pass Criteria**: ✅ All errors user-friendly and actionable

---

### Test 6.4: File Type Indicators
**Objective**: Verify file type badges/icons

**Test**:
- Upload `.rpgle` file → RPG badge/icon
- Upload `.cl` file → CL badge/icon
- Upload `.sql` file → SQL badge/icon

**Pass Criteria**: ✅ Correct badge for each file type

---

### Test 6.5: Mobile Responsiveness
**Objective**: Verify mobile-friendly design

**Test Devices**:
- iPhone (Safari)
- Android (Chrome)
- iPad (Safari)

**Steps**:
1. Navigate to upload page on mobile
2. Test drag-drop (may need alternative on mobile)
3. Test file selection via file picker
4. Verify upload works
5. Verify quota indicator visible
6. Verify file list scrollable

**Pass Criteria**: ✅ Fully functional on mobile devices

---

### Test 6.6: Accessibility
**Objective**: Verify keyboard navigation and screen reader support

**Test**:
- Tab through upload interface
- Press Enter to open file picker
- Use arrow keys to navigate file list
- Test with screen reader (VoiceOver/NVDA)

**Pass Criteria**: ✅ All functions accessible via keyboard, screen reader friendly

---

## 7. Cleanup & Expiration Testing

### Test 7.1: 24-Hour Auto-Deletion
**Objective**: Verify files deleted after 24 hours

**Method**:
1. Upload test file
2. Note `expires_at` timestamp
3. Wait 24 hours OR manually trigger cleanup:
   ```bash
   curl -X POST https://mcpress-chatbot-production.up.railway.app/api/code/admin/cleanup \
     -H "Authorization: Bearer ADMIN_TOKEN"
   ```
4. Verify file deleted from:
   - Filesystem (`/tmp/code-uploads/`)
   - Database (deleted_at timestamp set)
   - File list (no longer appears)

**Pass Criteria**: ✅ Files deleted within 1 hour of expiration

---

### Test 7.2: Cleanup Scheduler Running
**Objective**: Verify hourly cleanup job is active

**Method**: Check Railway logs for cleanup messages

```bash
railway logs --tail 100 | grep -i "cleanup"
```

**Expected Log Output**:
```
[Cleanup] Starting hourly cleanup task
[Cleanup] Deleted 5 expired files, freed 12MB
[Cleanup] Cleanup completed successfully
```

**Pass Criteria**: ✅ Cleanup runs every hour, logs visible

---

### Test 7.3: Weekly Purge of Deleted Files
**Objective**: Verify old deleted_at records purged weekly

**SQL Check**:
```sql
SELECT COUNT(*) FROM code_uploads WHERE deleted_at < NOW() - INTERVAL '7 days';
-- Should be 0 after purge runs
```

**Pass Criteria**: ✅ Old deleted records removed weekly

---

## 8. Performance Testing

### Test 8.1: Upload Speed
**Objective**: Verify upload performance meets SLA

**Test**:
- Upload 1MB file → Should complete in <3 seconds
- Upload 5MB file → Should complete in <10 seconds
- Upload 10MB file → Should complete in <20 seconds

**Pass Criteria**: ✅ All uploads within time limits

---

### Test 8.2: Concurrent Uploads
**Objective**: Verify system handles multiple simultaneous uploads

**Test**:
1. Simulate 10 users uploading files simultaneously
2. Monitor backend CPU/memory via Railway dashboard
3. Verify all uploads succeed
4. Check for errors in logs

**Pass Criteria**: ✅ All uploads succeed, no server errors

---

### Test 8.3: Database Performance
**Objective**: Verify database queries performant

**SQL Check**:
```sql
EXPLAIN ANALYZE SELECT * FROM code_uploads WHERE user_id = 'test-user';
-- Should use idx_code_uploads_user index, <10ms
```

**Pass Criteria**: ✅ All queries use indexes, <50ms response time

---

### Test 8.4: File List Load Time
**Objective**: Verify file list loads quickly

**Test**:
1. Upload 50 files (max daily quota)
2. Refresh file list
3. Measure load time

**Expected**: <1 second to load 50 files

**Pass Criteria**: ✅ File list loads in <1s

---

## 9. Integration Testing

### Test 9.1: Database Consistency
**Objective**: Verify DB records match filesystem

**Test**:
1. Upload 5 files
2. Query database for file records
3. Check filesystem for physical files
4. Verify counts match

**SQL**:
```sql
SELECT COUNT(*) FROM code_uploads WHERE deleted_at IS NULL;
-- Should match filesystem file count
```

**Pass Criteria**: ✅ DB and filesystem in sync

---

### Test 9.2: Session Management
**Objective**: Verify session lifecycle

**Test**:
1. Create session → Verify DB record
2. Upload files → Verify session.total_files increments
3. Session expires (24hr) → Verify status='expired'
4. Attempt to upload to expired session → Verify rejection

**Pass Criteria**: ✅ Session lifecycle managed correctly

---

### Test 9.3: Health Check Integration
**Objective**: Verify `/health` endpoint includes code upload status

**Test**:
```bash
curl https://mcpress-chatbot-production.up.railway.app/health
```

**Expected Response** (should include):
```json
{
  "status": "healthy",
  "code_upload_system": "operational",
  "cleanup_scheduler": "running"
}
```

**Pass Criteria**: ✅ Health check includes code upload status

---

## Test Results Template

Copy this for each test:

```
### Test X.X: [Test Name]
- **Date**: YYYY-MM-DD
- **Tester**: Name
- **Result**: ✅ PASS / ❌ FAIL
- **Notes**: [Any observations, bugs found, etc.]
- **Evidence**: [Screenshots, logs, API responses]
```

---

## Bug Reporting Template

If bugs found:

```
**Bug ID**: BUG-006-XXX
**Severity**: Critical / High / Medium / Low
**Test Case**: Test X.X
**Description**: [What went wrong]
**Steps to Reproduce**:
1. Step 1
2. Step 2
3. Step 3
**Expected**: [What should happen]
**Actual**: [What actually happened]
**Evidence**: [Screenshots, logs, error messages]
**Assigned To**: Dexter (Dev Agent)
```

---

## Acceptance Criteria Checklist

From Story-006:

- [ ] Support code file types: .rpg, .rpgle, .sqlrpgle, .cl, .clle, .sql, .txt
- [ ] File size limit: 10MB per file
- [ ] Multiple file upload: Up to 10 files simultaneously
- [ ] File type validation with clear error messages
- [ ] Temporary storage with 24-hour auto-deletion
- [ ] Upload progress indicators
- [ ] File preview before analysis
- [ ] Drag-and-drop interface
- [ ] File list management (remove before analysis)
- [ ] User quota tracking (prevent abuse)
- [ ] Mobile-responsive upload interface

---

## Definition of Done Checklist

- [ ] All acceptance criteria met
- [ ] All API endpoints tested and working
- [ ] All security tests passed
- [ ] Frontend UI/UX tested across browsers
- [ ] Mobile responsiveness verified
- [ ] Performance benchmarks met
- [ ] No critical or high-severity bugs
- [ ] Cleanup scheduler verified running
- [ ] Database migration verified
- [ ] Health check endpoint updated
- [ ] QA results documented in Story-006 file
- [ ] Story status updated to "QA Complete" or "Ready for Production"

---

## Post-Test Actions

1. **Document Results**:
   - Update Story-006 with QA Results section
   - List all tests performed
   - Note pass/fail for each category
   - Document any bugs found

2. **Create Bug Tickets**:
   - File bugs for any failures
   - Prioritize by severity
   - Assign to dev agent for fixes

3. **Retest After Fixes**:
   - Regression test all fixed bugs
   - Verify no new issues introduced

4. **Sign-Off**:
   - QA sign-off when all tests pass
   - Dev sign-off when code ready
   - Product owner (Kevin) final approval

---

**Testing Notes**:
- Prioritize critical path tests first (upload flow, validation, security)
- Document all API responses for debugging
- Take screenshots of UI states (success, error, loading)
- Monitor Railway logs during testing for backend errors
- Test on multiple browsers (Chrome, Firefox, Safari)
- Test on mobile devices (iOS, Android)

**Estimated Testing Time**: 4-6 hours for comprehensive testing

---

**Document Version**: 1.0
**Created By**: Quinn (QA Agent)
**Last Updated**: October 14, 2025
