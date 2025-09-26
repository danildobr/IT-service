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
        """Экспортирует ВСЕ заявки в Excel с вложенными скриншотами"""
        try:
            with Session() as session:
                tickets = session.query(Ticket).order_by(Ticket.created_at.desc()).all()
                if not tickets:
                    bot.reply_to(message, "📭 Нет заявок.")
                    return

                wb = Workbook()
                ws = wb.active
                ws.title = "Все заявки"

                # Заголовки
                headers = ["ID", "Пользователь", "Категория", "Подкатегория", "Описание", "Статус", "Дата", "Скриншот"]
                ws.append(headers)
                for cell in ws[1]:
                    cell.font = Font(bold=True)

                row_num = 2
                temp_files = []  # для удаления потом

                for ticket in tickets:
                    # Основные данные
                    username = f"@{ticket.user.username}" if ticket.user.username else f"ID{ticket.user.telegram_id}"
                    category = f"{ticket.subcategory.category.name} → {ticket.subcategory.name}"
                    desc = ticket.description or ""
                    status = ticket.status
                    date_str = ticket.created_at.strftime('%d.%m.%Y %H:%M')

                    ws.append([ticket.id, username, category, ticket.subcategory.name, desc, status, date_str, ""])

                    # Обработка скриншота
                    if ticket.screenshot:
                        try:
                            # Сохраняем бинарник во временный файл
                            img_ext = 'png'  # Telegram присылает в PNG
                            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{img_ext}") as tmp_img:
                                tmp_img.write(ticket.screenshot)
                                img_path = tmp_img.name
                                temp_files.append(img_path)

                            # Вставляем изображение в Excel
                            img = ExcelImage(img_path)
                            img.width = 150  # уменьшаем
                            img.height = 100
                            ws.add_image(img, f"H{row_num}")

                            # Подгоняем высоту строки
                            ws.row_dimensions[row_num].height = 80

                        except Exception as e:
                            print(f"Ошибка вставки скриншота заявки {ticket.id}: {e}")

                    row_num += 1

                # Автоширина
                for col in "ABCDEFG":
                    ws.column_dimensions[col].width = 20
                ws.column_dimensions["H"].width = 25  # для картинок

                # Сохраняем Excel
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_excel:
                    wb.save(tmp_excel.name)
                    excel_path = tmp_excel.name

                # Отправляем
                with open(excel_path, 'rb') as f:
                    bot.send_document(
                        message.chat.id,
                        f,
                        caption="📋 Все заявки",
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
            


    # @bot.message_handler(func=lambda msg: msg.text == "Запросить дополнительную информацию")
    # @it_specialist_required
    # def request_additional_info(message):
    #     """Запросить дополнительную информацию"""
    #     try:
    #         ticket_id = int(message.text.split()[1])
    #         with Session() as session:
    #             ticket = session.query(Ticket).filter_by(id=ticket_id).first()
    #             if not ticket:
    #                 bot.reply_to(message, "❌ Заявка не найдена")
    #                 return
                
    #             msg = bot.reply_to(message, 
    #                 f"✏️ Введите запрос дополнительной информации по заявке #{ticket_id}:\n"
    #                 "(Пользователь получит это сообщение)")
                
    #             bot.register_next_step_handler(msg, process_info_request, ticket_id)
                
    #     except (IndexError, ValueError):
    #         bot.reply_to(message, "❌ Использование: /request_info <номер_заявки>")

    # def process_info_request(message, ticket_id):
    #     """Обработка запроса информации"""
    #     with Session() as session:
    #         ticket = session.query(Ticket).filter_by(id=ticket_id).first()
    #         if not ticket:
    #             bot.reply_to(message, "❌ Заявка не найдена")
    #             return
            
    #         ticket.status = 'Ожидает уточнений'
    #         session.commit()
            
    #         # Отправляем запрос пользователю
    #         try:
    #             bot.send_message(
    #                 ticket.user.telegram_id,
    #                 f"ℹ️ По вашей заявке #{ticket.id} требуется дополнительная информация:\n\n"
    #                 f"{message.text}\n\n"
    #                 f"Пожалуйста, ответьте на это сообщение"
    #             )
    #             bot.reply_to(message, f"✅ Запрос отправлен пользователю @{ticket.user.username}")
    #         except Exception as e:
    #             bot.reply_to(message, f"❌ Ошибка отправки запроса: {e}")
                
                
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
        bot.register_next_step_handler(msg, _ask_clarification_text)


    def _ask_clarification_text(message):
        """Получаем ID заявки и запрашиваем текст вопроса"""
        try:
            ticket_id = int(message.text.strip())
            with Session() as session:
                ticket = session.query(Ticket).filter_by(id=ticket_id).first()
                if not ticket:
                    bot.reply_to(message, "❌ Заявка не найдена.")
                    return

                # Проверяем, что заявка назначена именно этому IT-специалисту
                if ticket.assigned_to != message.from_user.id:
                    bot.reply_to(message, "❌ Эта заявка не назначена вам.")
                    return

                if ticket.status == "Закрыта":
                    bot.reply_to(message, "❌ Заявка уже закрыта.")
                    return

                # Сохраняем ticket_id и запрашиваем текст
                bot.register_next_step_handler(
                    bot.reply_to(message, "Напишите вопрос пользователю:"),
                    _process_clarification_request,
                    ticket_id=ticket_id
                )
        except ValueError:
            bot.reply_to(message, "❌ Неверный ID. Введите число.")


    def _process_clarification_request(message, ticket_id):
        """Отправляем вопрос пользователю и меняем статус на 'Ждет уточнений'"""
        question = message.text.strip()
        if not question:
            bot.reply_to(message, "❌ Вопрос не может быть пустым.")
            return

        with Session() as session:
            ticket = session.query(Ticket).filter_by(id=ticket_id).first()
            if not ticket or ticket.assigned_to != message.from_user.id:
                bot.reply_to(message, "❌ Заявка не найдена или не назначена вам.")
                return

            # Меняем статус
            ticket.status = "Ждет уточнений"
            session.commit()

            # Отправляем пользователю
            try:
                bot.send_message(
                    ticket.user.telegram_id,
                    f"👨‍💻 IT-специалист запросил уточнение по заявке #{ticket.id}:\n"
                    f"«Вы можете прикрепить фото или документ, Введите ответ в одном сообщение»\n\n"
                    f"«Текст от специалиста: {question}»"
                )
                bot.reply_to(message, f"✅ Вопрос отправлен пользователю по заявке #{ticket_id}.")
            except Exception as e:
                bot.reply_to(message, "❌ Не удалось отправить сообщение (пользователь, возможно, заблокировал бота).")