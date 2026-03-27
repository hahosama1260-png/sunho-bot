from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from datetime import datetime

# ===== 키 설정 =====
TELEGRAM_TOKEN = "8675137094:AAHeB8RHh2ZPDBxuS8i0g4QXreH3GYwTWn4"
ADMIN_ID = 8498001355
CHANNEL_ID = "@hoho202012"
# =================

polls = {}

def is_admin(user_id):
    return user_id == ADMIN_ID

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.new_chat_members:
        for member in update.message.new_chat_members:
            await update.message.reply_text(
                "안녕하세요 선호실장 공지/이벤트 안내방입니다~\n"
                "앞으로 많은 혜택 받아보시고 궁금하신점은 @amg0090 텔 주시면 빠르게 응대 도와드리겠습니다 😊"
            )

async def notice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("❌ 관리자만 공지할 수 있어요!")
        return
    if not context.args:
        await update.effective_message.reply_text("사용법: /n [내용]")
        return
    text = " ".join(context.args)
    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=f"📢 공지사항\n\n{text}\n\n문의: @amg0090"
    )
    await update.effective_message.reply_text("✅ 공지 전송 완료!")

async def poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("❌ 관리자만 투표를 만들 수 있어요!")
        return
    if len(context.args) < 2:
        await update.effective_message.reply_text(
            "사용법: /p [제목] [경기1] [경기2]\n"
            "예시: /p 야구승패예측 롯데vs기아 요미우리vs지바롯데"
        )
        return
    title = context.args[0]
    matches = context.args[1:]
    now = datetime.now()
    poll_id = now.strftime('%H%M%S')

    polls[poll_id] = {
        'title': title,
        'matches': {},
        'voters': {},
        'active': True,
        'created_at': now
    }

    for match in matches:
        if 'vs' in match:
            teams = match.split('vs')
            polls[poll_id]['matches'][match] = {
                'team1': {'name': teams[0], 'voters': []},
                'team2': {'name': teams[1], 'voters': []},
            }
            polls[poll_id]['voters'][match] = []

    keyboard = []
    text = f"🏆 선호실장 {title}\n"
    text += "━━━━━━━━━━━━━━\n"
    for i, match in enumerate(matches, 1):
        if 'vs' in match:
            teams = match.split('vs')
            text += f"\n{i}. {teams[0]} vs {teams[1]}\n"
            row = [
                InlineKeyboardButton(f"✅ {teams[0]}", callback_data=f"v|{poll_id}|{match}|team1"),
                InlineKeyboardButton(f"✅ {teams[1]}", callback_data=f"v|{poll_id}|{match}|team2"),
            ]
            keyboard.append(row)

    text += "\n━━━━━━━━━━━━━━\n"
    text += "✅ 각 경기당 1회만 투표 가능"
    keyboard.append([InlineKeyboardButton("📊 실시간 현황", callback_data=f"v|{poll_id}|all|result")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    poll_msg = await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=text,
        reply_markup=reply_markup
    )
    polls[poll_id]['message_id'] = poll_msg.message_id
    await update.effective_message.reply_text(f"✅ 투표 전송 완료!\n투표 ID: {poll_id}")

async def endpoll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("❌ 관리자만 마감할 수 있어요!")
        return
    if not context.args:
        active_polls = [pid for pid, p in polls.items() if p['active']]
        if not active_polls:
            await update.effective_message.reply_text("진행 중인 투표가 없어요!")
            return
        poll_list = "\n".join([f"ID: {pid} - {polls[pid]['title']}" for pid in active_polls])
        await update.effective_message.reply_text(f"진행 중인 투표:\n{poll_list}\n\n마감: /end [ID]")
        return
    poll_id = context.args[0]
    if poll_id not in polls:
        await update.effective_message.reply_text("해당 투표를 찾을 수 없어요!")
        return
    polls[poll_id]['active'] = False
    poll_data = polls[poll_id]
    result_text = f"🏆 [{poll_data['title']}] 최종 결과\n━━━━━━━━━━━━━━\n"
    for match, data in poll_data['matches'].items():
        teams = match.split('vs')
        t1 = len(data['team1']['voters'])
        t2 = len(data['team2']['voters'])
        total = t1 + t2
        result_text += f"\n⚽ {teams[0]} vs {teams[1]}\n"
        if total > 0:
            t1_pct = int(t1 / total * 10)
            t2_pct = int(t2 / total * 10)
            result_text += f"{teams[0]}: {'🟦' * t1_pct}{'⬜' * (10-t1_pct)} {t1}표\n"
            result_text += f"{teams[1]}: {'🟥' * t2_pct}{'⬜' * (10-t2_pct)} {t2}표\n"
        else:
            result_text += "투표 없음\n"
    result_text += "\n━━━━━━━━━━━━━━\n🔒 투표 마감"
    await context.bot.send_message(chat_id=CHANNEL_ID, text=result_text)
    await update.effective_message.reply_text("✅ 투표 마감 완료!")

async def voters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("❌ 관리자만 확인할 수 있어요!")
        return
    if not context.args:
        active_polls = [pid for pid, p in polls.items() if p['active']]
        if not active_polls:
            await update.effective_message.reply_text("진행 중인 투표가 없어요!")
            return
        poll_list = "\n".join([f"ID: {pid} - {polls[pid]['title']}" for pid in active_polls])
        await update.effective_message.reply_text(f"진행 중인 투표:\n{poll_list}\n\n확인: /v [ID]")
        return
    poll_id = context.args[0]
    if poll_id not in polls:
        await update.effective_message.reply_text("해당 투표를 찾을 수 없어요!")
        return
    poll_data = polls[poll_id]
    result_text = f"👥 [{poll_data['title']}] 투표자\n━━━━━━━━━━━━━━\n"
    for match, data in poll_data['matches'].items():
        teams = match.split('vs')
        result_text += f"\n⚽ {teams[0]} vs {teams[1]}\n"
        result_text += f"{teams[0]}: {', '.join(data['team1']['voters']) or '없음'}\n"
        result_text += f"{teams[1]}: {', '.join(data['team2']['voters']) or '없음'}\n"
    await update.effective_message.reply_text(result_text)

async def vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        parts = query.data.split("|")
        action = parts[0]
        poll_id = parts[1]
        match = parts[2]
        choice = parts[3]
    except:
        await query.answer("오류가 발생했어요!", show_alert=True)
        return

    if poll_id not in polls:
        await query.answer("투표가 종료되었습니다!", show_alert=True)
        return

    poll_data = polls[poll_id]

    if not poll_data['active']:
        await query.answer("🔒 투표가 마감되었습니다!", show_alert=True)
        return

    user_id = query.from_user.id
    user_name = query.from_user.first_name

    if choice == "result":
        result_text = f"📊 [{poll_data['title']}] 실시간 현황\n━━━━━━━━━━━━━━\n"
        for m, data in poll_data['matches'].items():
            teams = m.split('vs')
            t1 = len(data['team1']['voters'])
            t2 = len(data['team2']['voters'])
            total = t1 + t2
            result_text += f"\n⚽ {teams[0]} vs {teams[1]}\n"
            if total > 0:
                t1_pct = int(t1 / total * 10)
                t2_pct = int(t2 / total * 10)
                result_text += f"{teams[0]}: {'🟦' * t1_pct}{'⬜' * (10-t1_pct)} {t1}표\n"
                result_text += f"{teams[1]}: {'🟥' * t2_pct}{'⬜' * (10-t2_pct)} {t2}표\n"
            else:
                result_text += "아직 투표 없음\n"
        await query.answer(result_text, show_alert=True)
        return

    if match not in poll_data['voters']:
        poll_data['voters'][match] = []

    if user_id in poll_data['voters'][match]:
        await query.answer("이미 이 경기에 투표하셨습니다! 🚫", show_alert=True)
        return

    poll_data['voters'][match].append(user_id)
    poll_data['matches'][match][choice]['voters'].append(user_name)
    await query.answer("✅ 투표 완료!", show_alert=True)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(CommandHandler("n", notice))
    app.add_handler(CommandHandler("p", poll))
    app.add_handler(CommandHandler("end", endpoll))
    app.add_handler(CommandHandler("v", voters))
    app.add_handler(CallbackQueryHandler(vote_callback))
    print("봇 시작됨!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
