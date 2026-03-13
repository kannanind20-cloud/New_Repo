Feature: User Login

  Background:
    Given User need to navigated to practicetestautomation

  Scenario: Verify login page
    When Enter student and Password123
    Then User should be redirected to logged in page

  Scenario: Verify login page with invalid username and password
    When User enters invalid username1 and password
    And Users clicks on Login button
    Then User not logged in due to invalid username and password
#Feature: User Login
#  Background:
#    Given User need to navigated to practicetestautomation
#  Scenario: Verify login page
#    When Enter student and Password123
#    Then User should be redirected to logged in page
#
#  Scenario: Verify login page with invalid username and password
#    When User enters invalid username1 and password
#    And Users clicks on Login button
#    #Then User not logged in due to invalid username and password