#!/bin/bash
set -e
cd /home/user/Doubao/chats/38447255748799234

# === MD 181s ===
echo "=== MD ==="
python3 render_md.py 0 90 md_a.mp4 > mda.log 2>&1
python3 render_md.py 90 91 md_b.mp4 > mdb.log 2>&1
ffmpeg -y -i md_a.mp4 -i md_b.mp4 -filter_complex "[0:v][1:v]concat=n=2:v=1[v]" -map "[v]" -c:v libx264 -crf 20 -pix_fmt yuv420p md_full_nosound.mp4 2>/dev/null
ffmpeg -y -i md_full_nosound.mp4 -i md_song/0001338197913165.mp3 -i hit_sfx_md.wav -filter_complex "[1:a]anull[music];[2:a]volume=10.2[hit];[music][hit]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k md_full_16x9.mp4 2>/dev/null
echo "MD done"

# === RB 220s ===
echo "=== RB ==="
python3 render_rebuff.py 0 110 rb_a.mp4 > rba.log 2>&1
python3 render_rebuff.py 110 110 rb_b.mp4 > rbb.log 2>&1
ffmpeg -y -i rb_a.mp4 -i rb_b.mp4 -filter_complex "[0:v][1:v]concat=n=2:v=1[v]" -map "[v]" -c:v libx264 -crf 20 -pix_fmt yuv420p rb_full_nosound.mp4 2>/dev/null
ffmpeg -y -i rb_full_nosound.mp4 -i rebuff_song/0002537707315429.mp3 -i hit_sfx_rebuff.wav -filter_complex "[1:a]anull[music];[2:a]volume=10.2[hit];[music][hit]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k rb_full_16x9.mp4 2>/dev/null
echo "RB done"

# === HTM 150s ===
echo "=== HTM ==="
python3 render_htm.py 0 75 ht_a.mp4 > hta.log 2>&1
python3 render_htm.py 75 75 ht_b.mp4 > htb.log 2>&1
ffmpeg -y -i ht_a.mp4 -i ht_b.mp4 -filter_complex "[0:v][1:v]concat=n=2:v=1[v]" -map "[v]" -c:v libx264 -crf 20 -pix_fmt yuv420p ht_full_nosound.mp4 2>/dev/null
ffmpeg -y -i ht_full_nosound.mp4 -i htm_song/0013526247710695.mp3 -i hit_sfx_htm.wav -filter_complex "[1:a]anull[music];[2:a]volume=10.2[hit];[music][hit]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k ht_full_16x9.mp4 2>/dev/null
echo "HTM done"

# === LR 560s (4段) ===
echo "=== LR ==="
python3 render_lr.py 0 140 lr_a.mp4 > lra.log 2>&1
python3 render_lr.py 140 140 lr_b.mp4 > lrb.log 2>&1
python3 render_lr.py 280 140 lr_c.mp4 > lrc.log 2>&1
python3 render_lr.py 420 140 lr_d.mp4 > lrd.log 2>&1
ffmpeg -y -i lr_a.mp4 -i lr_b.mp4 -i lr_c.mp4 -i lr_d.mp4 -filter_complex "[0:v][1:v][2:v][3:v]concat=n=4:v=1[v]" -map "[v]" -c:v libx264 -crf 20 -pix_fmt yuv420p lr_full_nosound.mp4 2>/dev/null
ffmpeg -y -i lr_full_nosound.mp4 -i lr_song/0001155783243191.mp3 -i hit_sfx_lr.wav -filter_complex "[1:a]anull[music];[2:a]volume=10.2[hit];[music][hit]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k lr_full_16x9.mp4 2>/dev/null
echo "LR done"
echo "ALL_RERENDER_DONE"
