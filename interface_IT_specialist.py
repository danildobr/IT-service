from openpyxl.styles import Font
import tempfile
from telebot import types
from openpyxl import Workbook
from models import *
from decorators import it_specialist_required
from openpyxl.drawing.image import Image as ExcelImage

def register_it_handlers(bot):

    @bot.message_handler(func=lambda msg: msg.text == "📋 Все заявки")
    @it_specialist_required
    def export_all_tickets_excel(message):
        """Экспортирует ВСЕ заявки в Excel с вложенными скриншотами и указанием назначенного специалиста"""
        try:
            with Session() as session:
                tickets = session.query(Ticket).order_by(Ticket.created_at.desc()).all()
                if not tickets:
                    bot.reply_to(message, "📭 Нет заявок.")
                    return

                wb = Workbook()
                ws = wb.active
                ws.title = "Все заявки"

                # Заголовки — добавлен столбец "Назначен"
                headers = ["ID", "Пользователь", "Категория", "Подкатегория", "Описание", "Статус", "Назначен IT-специалист", "Дата", "Скриншот"]
                ws.append(headers)
                for cell in ws[1]:
                    cell.font = Font(bold=True)

                row_num = 2
                temp_files = []

                for ticket in tickets:
                    # Пользователь
                    username = f"@{ticket.user.username}" if ticket.user.username else f"ID{ticket.user.telegram_id}"
                    
                    # Категория
                    category = f"{ticket.subcategory.category.name} → {ticket.subcategory.name}"
                    desc = ticket.description or ""
                    status = ticket.status
                    date_str = ticket.created_at.strftime('%d.%m.%Y %H:%M')

                    # Назначенный IT-специалист
                    assigned_to = "— не назначен —"
                    if ticket.assigned_to:
                        it_user = session.query(User).filter_by(telegram_id=ticket.assigned_to).first()
                        if it_user:
                            assigned_to = f"@{it_user.username}" if it_user.username else f"ID{it_user.telegram_id}"

                    # Добавляем строку (обрати внимание: "Назначен" идёт перед "Дата")
                    ws.append([
                        ticket.id,
                        username,
                        category,
                        ticket.subcategory.name,
                        desc,
                        status,
                        assigned_to,
                        date_str,
                        ""
                    ])

                    # Обработка скриншота
                    if ticket.screenshot:
                        try:
                            img_ext = 'png'
                            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{img_ext}") as tmp_img:
                                tmp_img.write(ticket.screenshot)
                                img_path = tmp_img.name
                                temp_files.append(img_path)

                            img = ExcelImage(img_path)
                            img.width = 150
                            img.height = 100
                            ws.add_image(img, f"I{row_num}")  # ← столбец I (был H)

                            ws.row_dimensions[row_num].height = 80

                        except Exception as e:
                            print(f"Ошибка вставки скриншота заявки {ticket.id}: {e}")

                    row_num += 1

                # Автоширина (обновляем до столбца I)
                for col in "ABCDEFGH":  # A–H (I — картинки, ширина отдельно)
                    ws.column_dimensions[col].width = 20
                ws.column_dimensions["I"].width = 25  # для картинок

                # Сохраняем и отправляем
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_excel:
                    wb.save(tmp_excel.name)
                    excel_path = tmp_excel.name

                with open(excel_path, 'rb') as f:
                    bot.send_document(
                        message.chat.id,
                        f,
                        caption="📋 Все заявки (с назначением)",
                        visible_file_name="Все_заявки.xlsx"
                    )

                # Удаляем временные файлы
                os.unlink(excel_path)
                for f in temp_files:
                    try:
                        os.unlink(f)
                    except:
                        pass

        except Exception as e:
            bot.reply_to(message, f"❌ Ошибка экспорта: {str(e)}")
            print("Ошибка экспорта заявок:", e)
            if 'excel_path' in locals():
                try:
                    os.unlink(excel_path)
                except:
                    pass

    @bot.message_handler(func=lambda msg: msg.text == "✅ Закрыть заявку")
    @it_specialist_required
    def close_ticket_start(message):
        """Начало закрытия заявки: запрос ID"""
        msg = bot.reply_to(message, "Введите ID заявки для закрытия:")
        bot.register_next_step_handler(msg, _ask_close_ticket_confirmation)


    def _ask_close_ticket_confirmation(message):
        """Показывает подтверждение закрытия"""
        try:
            ticket_id = int(message.text.strip())
            
            with Session() as session:
                ticket = session.query(Ticket).filter_by(id=ticket_id).first()
                if not ticket:
                    bot.reply_to(message, "❌ Заявка не найдена.")
                    return

                if ticket.status == "Закрыта":
                    bot.reply_to(message, f"ℹ️ Заявка #{ticket_id} уже закрыта.")
                    return

                # Формируем краткое описание
                username = f"@{ticket.user.username}" if ticket.user.username else f"ID{ticket.user.telegram_id}"
                category = f"{ticket.subcategory.category.name} → {ticket.subcategory.name}"
                short_desc = (ticket.description[:60] + '...') if len(ticket.description) > 60 else ticket.description

                # Кнопки подтверждения
                markup = types.InlineKeyboardMarkup()
                markup.row(
                    types.InlineKeyboardButton("✅ Да, закрыть", callback_data=f"confirm_close_{ticket_id}"),
                    types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_close")
                )

                bot.send_message(
                    message.chat.id,
                    f"❓ Точно закрыть заявку <b>#{ticket_id}</b>?\n\n"
                    f"Пользователь: {username}\n"
                    f"Категория: {category}\n"
                    f"Описание: {short_desc}\n"
                    f"Текущий статус: {ticket.status}",
                    reply_markup=markup,
                    parse_mode='HTML'
                )

        except ValueError:
            bot.reply_to(message, "❌ Неверный формат ID. Надо ввести число. Воспользуйтесь еще раз командой '✅ Закрыть заявку' ")
        except Exception as e:
            bot.reply_to(message, f"❌ Ошибка: {str(e)}")


    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_close_"))
    @it_specialist_required
    def confirm_close_ticket(call):
        """Подтверждение закрытия заявки"""
        try:
            ticket_id = int(call.data.split("_")[-1])
            
            with Session() as session:
                ticket = session.query(Ticket).filter_by(id=ticket_id).first()
                if not ticket:
                    bot.answer_callback_query(call.id, "Заявка не найдена")
                    return

                if ticket.status == "Закрыта":
                    bot.edit_message_text(
                        f"ℹ️ Заявка #{ticket_id} уже закрыта.",
                        call.message.chat.id,
                        call.message.message_id
                    )
                    return

                # Обновляем статус
                ticket.status = "Закрыта"
                ticket.closed_at = datetime.now()
                session.commit()

                bot.edit_message_text(
                    f"✅ Заявка #{ticket_id} успешно закрыта!",
                    call.message.chat.id,
                    call.message.message_id
                )

                # Уведомляем пользователя
                try:
                    bot.send_message(
                        ticket.user.telegram_id,
                        f"✅ Ваша заявка #{ticket_id} закрыта.\n"
                        "Спасибо за обращение!"
                    )
                except:
                    pass  # Пользователь заблокировал бота — игнорируем

        except Exception as e:
            bot.edit_message_text(
                f"❌ Ошибка закрытия: {str(e)}",
                call.message.chat.id,
                call.message.message_id
            )


    @bot.callback_query_handler(func=lambda call: call.data == "cancel_close")
    def cancel_close_ticket(call):
        """Отмена закрытия заявки"""
        bot.edit_message_text(
            "❌ Закрытие отменено.",
            call.message.chat.id,
            call.message.message_id
        )
            
    
    @bot.message_handler(func=lambda msg: msg.text == "🔄 Взять заявку")
    @it_specialist_required
    def start_take_ticket(message):
        msg = bot.reply_to(message, "Введите ID заявки для взятия в работу:")
        bot.register_next_step_handler(msg, _ask_take_confirmation)


    def _ask_take_confirmation(message):
        try:
            ticket_id = int(message.text.strip())
            with Session() as session:
                ticket = session.query(Ticket).filter_by(id=ticket_id).first()
                if not ticket:
                    bot.reply_to(message, "❌ Заявка не найдена.")
                    return

                if ticket.status != "Открыта":
                    if ticket.status == "В работе" and ticket.assigned_to:
                        # Ищем IT-специалиста по telegram_id
                        it_specialist = session.query(User).filter_by(telegram_id=ticket.assigned_to).first()
                        if it_specialist:
                            spec_name = f"@{it_specialist.username}" if it_specialist.username else f"ID {it_specialist.telegram_id}"
                            bot.reply_to(
                                message,
                                f"❌ Заявка уже в работе за IT-специалистом: {spec_name}.\n"
                                f"Текущий статус: {ticket.status}"
                            )
                        else:
                            bot.reply_to(
                                message,
                                f"❌ Заявка уже в работе (специалист не найден в БД).\n"
                                f"Текущий статус: {ticket.status}"
                            )
                    else:
                        bot.reply_to(
                            message,
                            f"❌ Заявка недоступна для взятия. Текущий статус: {ticket.status}"
                        )
                    return
                # Предпросмотр
                username = f"@{ticket.user.username}" if ticket.user.username else f"ID{ticket.user.telegram_id}"
                category = f"{ticket.subcategory.category.name} → {ticket.subcategory.name}"
                desc = (ticket.description[:60] + '...') if len(ticket.description) > 60 else ticket.description

                markup = types.InlineKeyboardMarkup()
                markup.row(
                    types.InlineKeyboardButton("✅ Взять в работу", callback_data=f"confirm_take_{ticket_id}"),
                    types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_take")
                )

                bot.send_message(
                    message.chat.id,
                    f"❓ Взять заявку #{ticket_id} в работу?\n\n"
                    f"Пользователь: {username}\n"
                    f"Категория: {category}\n"
                    f"Описание: {desc}",
                    reply_markup=markup,
                )

        except ValueError:
            bot.reply_to(message, "❌ Неверный ID. Введите число.")


    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_take_"))
    @it_specialist_required
    def confirm_take_ticket(call):
        ticket_id = int(call.data.split("_")[-1])
        with Session() as session:
            ticket = session.query(Ticket).filter_by(id=ticket_id).first()
            if not ticket:
                bot.answer_callback_query(call.id, "Заявка не найдена")
                return
            if ticket.status != "Открыта":
                bot.edit_message_text(
                    f"❌ Заявка уже обрабатывается. Статус: {ticket.status}",
                    call.message.chat.id,
                    call.message.message_id
                )
                return

            # Назначаем специалиста
            ticket.status = "В работе"
            ticket.assigned_to = call.from_user.id
            ticket.taken_at = datetime.now()
            session.commit()

            # Уведомляем пользователя
            try:
                bot.send_message(
                    ticket.user.telegram_id,
                    f"👨‍💻 Ваша заявка #{ticket_id} взята в работу IT-специалистом."
                )
            except:
                pass

            bot.edit_message_text(
                f"✅ Заявка #{ticket_id} успешно взята в работу!",
                call.message.chat.id,
                call.message.message_id
            )


    @bot.callback_query_handler(func=lambda call: call.data == "cancel_take")
    def cancel_take(call):
        bot.edit_message_text("❌ Взятие отменено.", call.message.chat.id, call.message.message_id)


    @bot.message_handler(func=lambda msg: msg.text == "Запросить дополнительную информацию")
    @it_specialist_required
    def start_request_clarification(message):
        """Начало запроса уточнения: спрашиваем ID заявки"""
        msg = bot.reply_to(message, "Введите ID заявки, по которой нужно запросить уточнение:")
        bot.register_next_step_handler(msg, _ask_clarification_content)


    def _ask_clarification_content(message):
        """Получаем ID заявки и запрашиваем контент (любой тип)"""
        try:
            ticket_id = int(message.text.strip())
            with Session() as session:
                ticket = session.query(Ticket).filter_by(id=ticket_id).first()
                if not ticket:
                    bot.reply_to(message, "❌ Заявка не найдена.")
                    return
                if ticket.assigned_to != message.from_user.id:
                    bot.reply_to(message, "❌ Эта заявка не назначена вам.")
                    return
                if ticket.status == "Закрыта":
                    bot.reply_to(message, "❌ Заявка уже закрыта.")
                    return

                # Сохраняем ticket_id и ждём контент
                msg = bot.reply_to(message, "Отправьте вопрос (текст, фото или файл):")
                bot.register_next_step_handler(
                    msg,
                    _ask_clarification_confirmation,
                    ticket_id=ticket_id
                )
        except ValueError:
            bot.reply_to(message, "❌ Неверный ID. Введите число.")


    def _ask_clarification_confirmation(message, ticket_id):
        """Показываем предпросмотр и запрашиваем подтверждение"""
        # Сохраняем данные сообщения для последующей отправки
        clarification_data = {
            'content_type': message.content_type,
            'text': message.text if message.content_type == 'text' else None,
            'file_id': None,
            'caption': None
        }

        if message.content_type == 'photo':
            clarification_data['file_id'] = message.photo[-1].file_id
            clarification_data['caption'] = message.caption
        elif message.content_type == 'document':
            clarification_data['file_id'] = message.document.file_id
            clarification_data['caption'] = message.caption

        # Предпросмотр
        if message.content_type == 'text':
            preview = f"📝 Текст:\n«{message.text[:100]}{'...' if len(message.text) > 100 else ''}»"
        elif message.content_type == 'photo':
            preview = "🖼️ Фото" + (f"\nПодпись: «{message.caption}»" if message.caption else "")
        elif message.content_type == 'document':
            preview = f"📎 Файл: {message.document.file_name}" + \
                    (f"\nПодпись: «{message.caption}»" if message.caption else "")
        else:
            bot.reply_to(message, "❌ Неподдерживаемый тип сообщения.")
            return

        # Кнопки подтверждения
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ Отправить", callback_data=f"confirm_clar_{ticket_id}"),
            types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_clar")
        )

        bot.send_message(
            message.chat.id,
            f"❓ Точно отправить это пользователю по заявке #{ticket_id}?\n\n{preview}",
            reply_markup=markup
        )

        # Сохраняем данные в кэш (временно)
        if not hasattr(bot, 'clarification_cache'):
            bot.clarification_cache = {}
        bot.clarification_cache[(message.from_user.id, ticket_id)] = clarification_data


    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_clar_"))
    @it_specialist_required
    def confirm_clarification(call):
        ticket_id = int(call.data.split("_")[-1])
        key = (call.from_user.id, ticket_id)

        if not hasattr(bot, 'clarification_cache') or key not in bot.clarification_cache:
            bot.answer_callback_query(call.id, "❌ Данные устарели. Начните сначала.")
            return

        data = bot.clarification_cache.pop(key)

        with Session() as session:
            ticket = session.query(Ticket).filter_by(id=ticket_id).first()
            if not ticket or ticket.assigned_to != call.from_user.id:
                bot.edit_message_text("❌ Заявка не найдена или не назначена вам.", call.message.chat.id, call.message.message_id)
                return

            # Меняем статус
            ticket.status = "Ждет уточнений"
            session.commit()

            # Отправляем пользователю
            try:
                if data['content_type'] == 'text':
                    bot.send_message(
                        ticket.user.telegram_id,
                        f"👨‍💻 IT-специалист запросил уточнение по заявке #{ticket.id}:\n\n«{data['text']}»"
                    )
                elif data['content_type'] == 'photo':
                    bot.send_photo(
                        ticket.user.telegram_id,
                        data['file_id'],
                        caption=f"👨‍💻 IT-специалист запросил уточнение по заявке #{ticket.id}" + \
                                (f"\n\n{data['caption']}" if data['caption'] else "")
                    )
                elif data['content_type'] == 'document':
                    bot.send_document(
                        ticket.user.telegram_id,
                        data['file_id'],
                        caption=f"👨‍💻 IT-специалист запросил уточнение по заявке #{ticket.id}" + \
                                (f"\n\n{data['caption']}" if data['caption'] else "")
                    )

                bot.edit_message_text(
                    f"✅ Уточнение отправлено пользователю по заявке #{ticket_id}.",
                    call.message.chat.id,
                    call.message.message_id
                )
            except Exception as e:
                print(f"Ошибка отправки уточнения: {e}")
                bot.edit_message_text(
                    "❌ Не удалось отправить сообщение (пользователь, возможно, заблокировал бота).",
                    call.message.chat.id,
                    call.message.message_id
                )


    @bot.callback_query_handler(func=lambda call: call.data == "cancel_clar")
    def cancel_clarification(call):
        bot.edit_message_text("❌ Отправка отменена.", call.message.chat.id, call.message.message_id)