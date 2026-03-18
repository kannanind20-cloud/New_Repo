from behave.__main__ import main

if __name__ == "__main__":
    main([
        "Sample1/Feature_File",
        "--format", "html",
        "--outfile", "reports/report.html"
    ])
# from behave.__main__ import main
#
# if __name__ == "__main__":
#     main([
#         "Sample1/Feature_File",
#         "--format", "html",
#         "--outfile", "reports/report.html"
#     ])
# from behave.__main__ import main as Behave
# if __name__ == '__main__':
#     Log= r"C:\Users\kkannan\PyCharmMiscProject\Sample1\Feature_File"
#     Log1=[Log]
#     Behave(Log1)