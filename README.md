# pool-reservation-bot
Source for telegram bot and side service which helped with some pool reservations during COVID-19.

My anonymous friend asked some help to reserve swimming sessions during COVID-19. The problem 
was that only limited number of persons can reserve a place for one swimming session and 
the reservation was happening following the "first-click-first-reserved place" scheme. Moreover, 
actual reservations were opened very early in the night, so it was very tiring to do for him/her 
all by hand.

This is a telegram bot which automated the registration procedure and allowed my friend to 
sleep in the nights and still enjoy morning and evening swims.

  * ```reservation_bot.py``` - telegram reservation bot that interacts with the user to schedule next reservation
  * ```reservation_service.py``` - looped service which performs actual reservations from the given list

For actual reservations I used Selenium module and the chromedriver.
