import anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from datetime import datetime, timedelta
import asyncio

# ===== 키 설정 =====
TELEGRAM_TOKEN = "8675137094:AAHeB8RHh2ZPDBxuS8i0g4QXreH3GYwTWn4"
ANTHROPIC_API_KEY = "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"
ADMIN_ID = 8498001355
# ===================

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
polls = {}

def is_admin(user_id):
    return user_id == ADMIN_ID

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        name = member.first_name
        await update.message.reply_text(
            f"👋 {name}님 환영합니다!\n"
            f"투자/주식 커뮤니티에 오신 것을 환영해요 📈\n"
            f"궁금한 점은 ?질문 으로 물어보세요!"
        )

async def notice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user.id):
        await update.message.reply_text("❌ 관리자만 공지할 수 있어요!")
        return
    if not context.args:
        await update.message.reply_text("사용법: /notice [내용]")
        return
    text = " ".join(context.args)
    await update.message.reply_text(f"📢 공지사항\n\n{text}")

async def poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user.id):
        await update.message.reply_text("❌ 관리자만 투표를 만들 수 있어요!")
        return
    if len(context.args) < 4:
        await update.message.reply_text("사용법: /poll [마감시간(분)] [제목] [선택1] [선택2] ...\n예) /poll 60 오늘장전망 상승 하락 보합")
        return
    minutes = int(context.args[0])
    title = context.args[1]
    options = context.args[2:]
    poll_id = str(update.message.message_id)
    end_time = datetime.now() + timedelta(minutes=minutes)
    polls[poll_id] = {
        "title": title,
        "options": {opt: [] for opt in options},
        "voters": [],
        "end_time": end_time,
        "chat_id": update.message.chat_id,
        "closed": False
    }
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"{poll_id}|{opt}")] for opt in options]
    keyboard.append([InlineKeyboardButton("📊 결과 보기", callback_data=f"{poll_id}|result")])
    msg = await update.message.reply_text(
        f"🗳 투표: {title}\n"
        f"⏰ 마감: {minutes}분 후 ({end_time.strftime('%H:%M')})\n\n"
        + "\n".join(f"• {opt}" for opt in options),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    asyncio.create_task(close_poll(context, poll_id, minutes * 60, msg.message_id))

async def close_poll(context, poll_id, seconds, message_id):
    await asyncio.sleep(seconds)
    if poll_id not in polls:
        return
    poll_data = polls[poll_id]
    poll_data["closed"] = True
    result = f"🏁 투표 마감! - {poll_data['title']}\n\n"
    total = sum(len(v) for v in poll_data['options'].values())
    if total == 0:
        result += "참여자가 없었어요 😢"
    else:
        for opt, voters in poll_data['options'].items():
            pct = (len(voters) / total * 100) if total > 0 else 0
            bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
            result += f"• {opt}\n  {bar} {len(voters)}표 ({pct:.1f}%)\n\n"
        result += f"총 참여자: {total}명"
    await context.bot.send_message(
        chat_id=poll_data["chat_id"],
        text=f"📢 투표 결과 공지\n\n{result}"
    )

async def vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("|")
    poll_id, choice = data[0], data[1]
    if poll_id not in polls:
        await query.answer("투표를 찾을 수 없어요!", show_alert=True)
        return
    poll_data = polls[poll_id]
    if poll_data["closed"]:
        await query.answer("이미 마감된 투표예요! 🚫", show_alert=True)
        return
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    if choice == "result":
        result = f"📊 현재 투표 현황: {poll_data['title']}\n\n"
        total = sum(len(v) for v in poll_data['options'].values())
        for opt, voters in poll_data['options'].items():
            pct = (len(voters) / total * 100) if total > 0 else 0
            result += f"• {opt}: {len(voters)}표 ({pct:.1f}%)\n"
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
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        result += f"• {opt}\n  {bar} {len(voters)}표 ({pct:.1f}%)\n\n"
    await query.edit_message_text(result, reply_markup=query.message.reply_markup)

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text.startswith("?"):
        return
    question = text[1:].strip()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": f"투자/주식 관련 질문입니다: {question}"}]
    )
    await update.message.reply_text(f"🤖 AI 답변:\n{response.content[0].text}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(CommandHandler("notice", notice))
    app.add_handler(CommandHandler("poll", poll))
    app.add_handler(CallbackQueryHandler(vote_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
    print("봇 시작됨!")
    app.run_polling()

if __name__ == "__main__":
    main()