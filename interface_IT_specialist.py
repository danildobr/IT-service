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
                        caption="📋 Все заявки (со скриншотами)",
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
            
    # @bot.message_handler(func=lambda msg: msg.text.startswith('/take_'))
    # @it_specialist_required
    # def take_ticket_command(message):
    #     """Команда взять в работу заявку """
    #     try:
    #         # Извлекаем номер заявки из команды
    #         ticket_id = int(message.text.split('_')[1])
    #         take_ticket_by_id(message, ticket_id)
    #     except (IndexError, ValueError):
    #         bot.reply_to(message, "❌ Использование: /take_<номер_заявки>")

    # def take_ticket_by_id(message, ticket_id):
    #     """Взять заявку в работу по ID"""
    #     with Session() as session:
    #         ticket = session.query(Ticket).filter_by(id=ticket_id, status='Открыт').first()
    #         if not ticket:
    #             bot.reply_to(message, "❌ Заявка не найдена или уже взята в работу")
    #             return
            
    #         user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    #         ticket.status = 'В работе'
    #         ticket.taken_at = datetime.now()
    #         session.commit()
            
    #         # Уведомление пользователя
    #         try:
    #             bot.send_message(
    #                 ticket.user.telegram_id,
    #                 f"🔄 Ваша заявка #{ticket.id} взята в работу\n"
    #                 f"Категория: {ticket.subcategory.category.name}\n"
    #                 f"Исполнитель: @{user.username}"
    #             )
    #         except Exception as e:
    #             print(f"Ошибка уведомления пользователя: {e}")
            
    #         bot.reply_to(message, f"✅ Вы взяли заявку #{ticket.id} в работу")
            
    # @bot.message_handler(func=lambda msg: msg.text.startswith('/close_'))
    # @it_specialist_required
    # def close_ticket_command(message):
    #     """Команда закрыть заявку"""
    #     try:
    #         # Извлекаем номер заявки из команды
    #         ticket_id = int(message.text.split('_')[1])
    #         close_ticket_by_id(message, ticket_id)
    #     except (IndexError, ValueError):
    #         bot.reply_to(message, "❌ Использование: /close_<номер_заявки>")

    # def close_ticket_by_id(message, ticket_id):
    #     """Закрыть заявку по ID"""
    #     with Session() as session:
    #         ticket = session.query(Ticket).filter_by(
    #             id=ticket_id, 
    #             status='В работе'
    #         ).first()
            
    #         if not ticket:
    #             bot.reply_to(message, "❌ Заявка не найдена или не в работе")
    #             return
            
    #         ticket.status = 'Закрыт'
    #         ticket.closed_at = datetime.now()
    #         session.commit()
            
    #         # Расчет времени выполнения
    #         time_spent = (ticket.closed_at - ticket.taken_at).total_seconds() / 60
            
    #         # Уведомление пользователя
    #         try:
    #             bot.send_message(
    #                 ticket.user.telegram_id,
    #                 f"✅ Ваша заявка #{ticket.id} закрыта\n"
    #                 f"Время решения: {int(time_spent)} минут\n"
    #                 f"Категория: {ticket.subcategory.category.name}"
    #             )
    #         except Exception as e:
    #             print(f"Ошибка уведомления пользователя: {e}")
            
    #         bot.reply_to(message, f"✅ Заявка #{ticket.id} закрыта. Время выполнения: {int(time_spent)} мин")


    # @bot.message_handler(func=lambda msg: msg.text == "📝 Мои заявки")
    # @it_specialist_required
    # def show_my_tickets(message):
    #     """Показать заявки в работе у специалиста"""
    #     with Session() as session:
    #         user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    #         tickets = session.query(Ticket).filter(
    #             Ticket.status == 'В работе'
    #         ).order_by(Ticket.taken_at.desc()).all()
            
    #         if not tickets:
    #             bot.reply_to(message, "У вас нет заявок в работе")
    #             return
            
    #         response = "📌 Ваши текущие заявки:\n\n"
    #         for ticket in tickets:
    #             time_in_work = (datetime.now() - ticket.taken_at).total_seconds() / 60
    #             response += (
    #                 f"🔹 #{ticket.id}\n"
    #                 f"Категория: {ticket.subcategory.category.name}\n"
    #                 f"Пользователь: @{ticket.user.username}\n"
    #                 f"В работе: {int(time_in_work)} мин\n"
    #                 f"Описание: {ticket.description}\n"
    #                 f"Дата: {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    #             )
            
    #         bot.reply_to(message, response)


    @bot.message_handler(func=lambda msg: msg.text == "Запросить дополнительную информацию")
    @it_specialist_required
    def request_additional_info(message):
        """Запросить дополнительную информацию"""
        try:
            ticket_id = int(message.text.split()[1])
            with Session() as session:
                ticket = session.query(Ticket).filter_by(id=ticket_id).first()
                if not ticket:
                    bot.reply_to(message, "❌ Заявка не найдена")
                    return
                
                msg = bot.reply_to(message, 
                    f"✏️ Введите запрос дополнительной информации по заявке #{ticket_id}:\n"
                    "(Пользователь получит это сообщение)")
                
                bot.register_next_step_handler(msg, process_info_request, ticket_id)
                
        except (IndexError, ValueError):
            bot.reply_to(message, "❌ Использование: /request_info <номер_заявки>")

    def process_info_request(message, ticket_id):
        """Обработка запроса информации"""
        with Session() as session:
            ticket = session.query(Ticket).filter_by(id=ticket_id).first()
            if not ticket:
                bot.reply_to(message, "❌ Заявка не найдена")
                return
            
            ticket.status = 'Ожидает уточнений'
            session.commit()
            
            # Отправляем запрос пользователю
            try:
                bot.send_message(
                    ticket.user.telegram_id,
                    f"ℹ️ По вашей заявке #{ticket.id} требуется дополнительная информация:\n\n"
                    f"{message.text}\n\n"
                    f"Пожалуйста, ответьте на это сообщение"
                )
                bot.reply_to(message, f"✅ Запрос отправлен пользователю @{ticket.user.username}")
            except Exception as e:
                bot.reply_to(message, f"❌ Ошибка отправки запроса: {e}")
                
                
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
            bot.reply_to(message, "❌ Неверный формат ID. Введите число.")
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
            

        

        
