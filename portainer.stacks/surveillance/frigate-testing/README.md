# Frigate Dahua VTO Two-Way Audio Testing

Minimal Frigate setup for testing Dahua VTO two-way audio (backchannel) on Windows.

## Quick Start

```bash
cd portainer.stacks/surveillance/frigate-testing
docker-compose up -d
```

**Access:** http://localhost:5011 (Frigate) | http://localhost:1984 (go2rtc)

## Prerequisites

1. **Docker Desktop** with WSL2 enabled
2. **Network access** to VTO at `192.168.0.15`
3. **VTO credentials** configured in `.env` file

## Critical Configuration Requirements

### 1. Script Line Endings (Windows Users!)

The `fix_vto_codecs.sh` script **MUST** have Unix (LF) line endings, not Windows (CRLF).

**Fix line endings:**
```bash
docker exec frigate-test sh -c "sed -i 's/\r$//' /config/fix_vto_codecs.sh"
```

Or convert before starting:
```bash
dos2unix config/fix_vto_codecs.sh
# OR
wsl sed -i 's/\r$//' config/fix_vto_codecs.sh
```

### 2. Stream Configuration Format

**Simple single-stream configuration:**

```yaml
vratnik:
  - echo:/config/fix_vto_codecs.sh rtsp://{FRIGATE_RTSP_CREDENTIALS}@192.168.0.15:554/cam/realmonitor?channel=1&subtype=0
```

**Alternative multiline format** (echo on one line, RTSP on next):
```yaml
vratnik:
  - echo:/config/fix_vto_codecs.sh
    rtsp://{FRIGATE_RTSP_CREDENTIALS}@192.168.0.15:554/cam/realmonitor?channel=1&subtype=0
```

**Important:**
- ✅ Quotes are optional (YAML multiline format works)
- ✅ Single stream provides **all 3 media types** when VTO is configured correctly
- ✅ No `#media=video` or `#media=audio` filters needed
- ✅ No `proto=Onvif` parameter (causes auth errors)
- ✅ No separate `#backchannel=1` stream needed

### 3. VTO Audio Codec Configuration

The script automatically configures:
- **Main stream (subtype=0)**: G.711A @ **8000Hz** (NOT 16000Hz - VTO limitation)
- **Sub stream (subtype=1)**: AAC @ 16000Hz

**Manual configuration** (if needed):
```bash
curl -sS --digest --globoff --user "admin:YOUR_VTO_PASSWORD" \
  "http://192.168.0.15/cgi-bin/configManager.cgi?action=setConfig&Encode[0].MainFormat[0].AudioEnable=true&Encode[0].MainFormat[0].Audio.Compression=G.711A&Encode[0].MainFormat[0].Audio.Frequency=8000&Encode[0].ExtraFormat[0].AudioEnable=true&Encode[0].ExtraFormat[0].Audio.Compression=AAC"
```

## Verification

### Check Stream Status

```bash
curl -s http://localhost:1984/api/streams | python -m json.tool | grep -A 5 '"medias"'
```

**Expected output** (3 media types = working!):
```json
"medias": [
    "video, recvonly, H264",
    "audio, recvonly, PCMA/8000",
    "audio, sendonly, PCMA/8000"  // ← Backchannel enabled!
]
```

### Verify VTO Configuration

```bash
curl -sS --digest --globoff --user "admin:YOUR_VTO_PASSWORD" \
  "http://192.168.0.15/cgi-bin/configManager.cgi?action=getConfig&name=Encode" | \
  grep -E "MainFormat\[0\].Audio\.(Compression|Frequency)"
```

**Expected:**
```
table.Encode[0].MainFormat[0].Audio.Compression=G.711A
table.Encode[0].MainFormat[0].Audio.Frequency=8000
```

## Common Issues & Solutions

### ❌ "No such file or directory" - Script Not Found

**Cause:** Windows CRLF line endings (`\r\n`) break the shebang `#!/bin/bash`

**Fix:**
```bash
docker exec frigate-test sh -c "sed -i 's/\r$//' /config/fix_vto_codecs.sh"
docker-compose restart
```

### ❌ Only 2 Media Types (Missing Backchannel)

**Possible causes:**

1. **Another Frigate instance has the backchannel**
   - VTO only supports **ONE** backchannel connection at a time
   - Stop other Frigate instances: `docker stop frigate`

2. **Echo script not running on backchannel stream**
   - Ensure **BOTH** vratnik streams have the echo prefix

3. **VTO not configured for G.711A @ 8kHz**
   - Run manual configuration command above
   - Restart streams: `curl -X DELETE http://localhost:1984/api/streams?src=vratnik`

### ❌ MSE Player Instead of WebRTC

**Causes:**
- Backchannel not connected (check media types above)
- WebRTC port 8555 not accessible
- Wrong WebRTC candidates in config

**Debug:**
```bash
# Check if port 8555 is accessible
nc -zv localhost 8555

# Check WebRTC candidates
docker exec frigate-test sh -c "cat /dev/shm/go2rtc.yaml | grep -A 5 webrtc"
```

### ❌ Authentication Errors

**Fix:** Remove `proto=Onvif` from URLs - it causes auth failures with this VTO model.

## Important Limitations

🚨 **VTO Backchannel Limit:** The Dahua VTO **only supports ONE active backchannel connection** at a time.

- If production Frigate is running, test environment won't get backchannel
- Stop production before testing: `docker stop frigate`
- Only one instance can have the microphone button active

## Diagnostic Commands

```bash
# Check stream status
curl -s http://localhost:1984/api/streams

# View logs
docker logs frigate-test --tail 50 -f

# Restart streams
curl -X DELETE http://localhost:1984/api/streams?src=vratnik

# Check VTO reachability
ping 192.168.0.15
nc -zv 192.168.0.15 554
```

## Troubleshooting Script

Run `test-streams.ps1` (PowerShell) for automated diagnostics:

```powershell
.\test-streams.ps1
```

This checks:
- Container status
- Stream connections
- Media types
- VTO configuration
- Common issues

## Success Checklist

- [ ] Script has Unix (LF) line endings
- [ ] Both vratnik streams have echo prefix
- [ ] No other Frigate instances running
- [ ] VTO configured to G.711A @ 8000Hz
- [ ] Stream shows 3 media types (video + audio recv + audio send)
- [ ] Frigate UI shows WebRTC player
- [ ] Microphone button appears in video controls

## Apply to Production

Once working here, update production config at:
```
portainer.stacks/surveillance/frigate/config.yml
```

Copy the exact stream configuration and restart production Frigate.

## Reference

Based on: https://github.com/felipecrs/dahua-vto-on-home-assistant

**Key difference:** This VTO requires G.711A @ **8000Hz** (not 16000Hz) and doesn't support the `proto=Onvif` parameter.
