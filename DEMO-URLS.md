# MC Press Chatbot Demo URLs

## Live Demo Access

**Frontend URL (Share this with your partner):**
```
https://heater-syndrome-intensive-hostel.trycloudflare.com
```

**Backend API URL:**
```
https://stopping-motor-metabolism-harassment.trycloudflare.com
```

## Important Notes

1. **Both servers must be running locally:**
   - Frontend: `npm run dev` (port 3005)
   - Backend: `uvicorn main:app --reload` (port 8000)

2. **Tunnels are running in background:**
   - Frontend tunnel PID: 41859
   - Backend tunnel PID: 41824

3. **To check if tunnels are still running:**
   ```bash
   ps aux | grep cloudflared
   ```

4. **To restart tunnels if needed:**
   ```bash
   # Kill existing tunnels
   pkill cloudflared
   
   # Start new tunnels
   nohup cloudflared tunnel --url http://localhost:8000 > backend-tunnel.log 2>&1 &
   nohup cloudflared tunnel --url http://localhost:3005 > frontend-tunnel.log 2>&1 &
   ```

5. **Important:** The frontend needs to be configured to use the backend tunnel URL. This is currently hardcoded in the frontend.

6. **If you see "Failed to load documents":** 
   - Hard refresh the browser (Cmd+Shift+R or Ctrl+Shift+F5)
   - The frontend may need to recompile after API URL changes
   - Check browser console for specific errors

## Monitoring

- Check tunnel logs: `tail -f backend-tunnel.log` or `tail -f frontend-tunnel.log`
- Check server logs for activity

## Duration

These free Cloudflare tunnels typically stay active for several hours but may disconnect after extended periods. For best reliability, restart them daily.