from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from datetime import datetime, timedelta

# ===== 키 설정 =====
TELEGRAM_TOKEN = "8675137094:AAHeB8RHh2ZPDBxuS8i0g4QXreH3GYwTWn4"
ADMIN_ID = 8498001355
CHANNEL_ID = "@sonho009"
# =================

polls = {}

def is_admin(user_id):
    return user_id == ADMIN_ID

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.new_chat_members:
        for member in update.message.new_chat_members:
            name = member.first_name
            await update.message.reply_text(
                f"👋 {name}님 환영합니다!\n"
                f"투자/주식 커뮤니티에 오신 것을 환영해요 📝\n"
                f"궁금한 점은 관리자에게 문의해주세요!"
            )

async def notice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("❌ 관리자만 공지할 수 있어요!")
        return
    if not context.args:
        await update.effective_message.reply_text("사용법: /notice [내용]")
        return
    text = " ".join(context.args)
    await context.bot.send_message(chat_id=CHANNEL_ID, text=f"📌 공지사항\n\n{text}")
    await update.effective_message.reply_text("✅ 공지 전송 완료!")

async def poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("❌ 관리자만 투표를 만들 수 있어요!")
        return
    if len(context.args) < 4:
        await update.effective_message.reply_text("사용법: /poll [마감시간(분)] [제목] [선택1] [선택2] ...\n예시: /poll 60 오늘장전망 상승 하락 보합")
        return
    try:
        minutes = int(context.args[0])
    except:
        await update.effective_message.reply_text("마감시간은 숫자로 입력해주세요!")
        return
    title = context.args[1]
    options = context.args[2:]
    end_time = datetime.now() + timedelta(minutes=minutes)
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"poll_{title}:{opt}") for opt in options]]
    keyboard.append([InlineKeyboardButton("📊 결과 보기", callback_data=f"poll_{title}:result")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    end_str = end_time.strftime('%H:%M')
    poll_msg = await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=f"📊 투표: {title}\n⏰ 마감: {end_str}\n\n아래 버튼을 눌러 투표하세요!",
        reply_markup=reply_markup
    )
    poll_id = str(poll_msg.message_id)
    polls[poll_id] = {
        'title': title,
        'options': {opt: [] for opt in options},
        'end_time': end_time,
        'voters': []
    }
    await update.effective_message.reply_text("✅ 투표 전송 완료!")

async def vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if not data.startswith("poll_"):
        return
    data = data[5:]
    parts = data.split(":")
    title = parts[0]
    choice = parts[1]
    poll_id = str(query.message.message_id)
    if poll_id not in polls:
        await query.answer("투표가 종료되었습니다!", show_alert=True)
        return
    poll_data = polls[poll_id]
    if datetime.now() > poll_data['end_time']:
        await query.answer("⏰ 투표 시간이 종료되었습니다!", show_alert=True)
        return
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    if choice == "result":
        result = f"📊 현재 투표 현황: {poll_data['title']}\n"
        total = sum(len(v) for v in poll_data['options'].values())
        end_str = poll_data['end_time'].strftime('%H:%M')
        result += f"⏰ 마감: {end_str}\n\n"
        for opt, voters in poll_data['options'].items():
            pct = (len(voters) / total * 100) if total > 0 else 0
            result += f"{opt}: {len(voters)}표 ({pct:.1f}%)\n"
        await query.answer(result, show_alert=True)
        return
    if user_id in poll_data['voters']:
        await query.answer("이미 투표하셨습니다! 중복 투표는 불가해요 🚫", show_alert=True)
        return
    poll_data['voters'].append(user_id)
    poll_data['options'][choice].append(user_name)
    result = f"📊 실시간 투표 현황: {poll_data['title']}\n"
    end_str = poll_data['end_time'].strftime('%H:%M')
    result += f"⏰ 마감: {end_str}\n\n"
    total = sum(len(v) for v in poll_data['options'].values())
    for opt, voters in poll_data['options'].items():
        pct = (len(voters) / total * 100) if total > 0 else 0
        bar = "🟩" * int(pct / 10) + "⬜" * (10 - int(pct / 10))
        result += f"{opt}\n  {bar} {len(voters)}표 ({pct:.1f}%)\n\n"
    await query.edit_message_text(result, reply_markup=query.message.reply_markup)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(CommandHandler("notice", notice))
    app.add_handler(CommandHandler("poll", poll))
    app.add_handler(CallbackQueryHandler(vote_callback))
    print("봇 시작됨!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
