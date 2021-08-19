# pool-reservation-bot
Source code for telegram bot and side service which helped with some pool reservations during COVID-19.

My friend asked me for some help to reserve swimming slots during COVID-19 pandemic. The problem 
was that only limited number of persons can reserve a slot per swimming session and 
the reservation was organized following the "first-click-first-served" scheme. Moreover, 
actual reservations were opened very early in the night, so it was very tiring to do 
everything by hand.

This is a telegram bot which automates the registration procedure and allows my friend to 
sleep at nights and then enjoy morning and evening swims.

  * ```reservation_bot.py``` - telegram reservation bot that interacts with the user to schedule next reservation
  * ```reservation_service.py``` - looped service which performs actual reservations from the list formed by the bot

For actual reservations I used Selenium module with the chromedriver bieng installed.
