# timew-budget: budgets for Timewarrior

```timew-budget``` is a Timewarrior[^1] extension that implements time budgeting. 

```console
user@host:~$ timew report timew-budget :yesterday
Tag         Time spent    Budgeted time    Budget surplus    Utilization
----------  ------------  ---------------  ----------------  -------------
routine     00:36:54      00:45:00         00:08:06          82.0%
bed         10:21:57      08:30:00         -01:51:57         121.95%
meditation  00:38:23      00:15:00         -00:23:23         255.89%
workout     01:03:44      03:15:00         02:11:16          32.68%
meal        00:29:32      01:30:00         01:00:28          32.81%
work        05:11:56      06:00:00         00:48:04          86.65%
plan        00:00:00      00:15:00         00:15:00          0.0%
content     00:00:00      01:00:00         01:00:00          0.0%
leisure     00:00:00      02:00:00         02:00:00          0.0%

Total       18:22:26      23:30:00         05:07:34          78.19%

Budget report for period 2025-01-01 to 2025-01-02
```

## Why?
Timewarrior is a fantastic tool for _tracking_ time, especially when integrated with Taskwarrior[^2], but it doesn't have a native way to normatively declare how much time you _should_ be spending on any given thing, or any way of comparing actual time spent against that.

```timew-budget``` allows you to define daily time budgets for intervals with certain tags in a simple YAML syntax, and uses the Timewarrior extensions API[^3] to compute how time is spent against those budgets over a given period of time.

```timew-budget```'s design was inspired heavily by ideas from Fava[^4]'s budgeting system and the Beancount[^5] plaintext accounting tool.

## Installation
1. Clone this repo to a directory of your choice.
2. Copy ```timew-budget.py``` into your Timewarrior extensions directory (default is ```~/.timewarrior/extensions/```). Alternatively, symlink ```timew-budget.py``` in that directory to the location of ```timew-budget.py``` in the cloned repo on your system. This is useful if you want to keep the extension up to date without copying it over every time you ```git pull```, or if you want to use another name to invoke the extension e.g. calling it ```budget.py``` instead of ```timew-budget.py```.
3. Copy ```timew-budget.yml``` into your Timewarrior directory (default is ```~/.timewarrior/```) or to some other location. *You should NOT symlink this to the repo*, because you'll need to customize this and a ```git pull``` will overwrite it.
4. Add the following line to your Timewarrior config file (default location is ```~/.timewarrior/timewarrior.cfg```): ```budget.file = ABSOLUTE_PATH_TO_YOUR_BUDGET_YML_FILE```. Don't put the path in quotes, Timewarrior doesn't seem to like this.
5. Install ```python3-tabulate``` using your package manager of choice.
6. You're ready to start using the extension. See the next section for usage instructions.

## Usage
Invoke the extension using the command ```timew report timew-budget PERIOD```. For PERIOD, Timewarrior's range hints or explicit dates will work - this is an extension, so Timewarrior is parsing the dates and passing them along. Try ```timew report timew-budget :today``` or ```timew report timew-budget :week```. ```timew-budget``` implements daily budgets, so it doesn't support ranges smaller than 24 hours. 

Next, you'll likely want to write your own budget file, so do that using the example file in this repo as a basis. See the Examples section for more details.

Once you've tweaked it to your needs, have fun!

## Definitions, syntax, and implementation
A budget is a _declaration of planned daily time expenditure_ on a given tag. All intervals with that tag, irrespective of any other tags, that occur during the report period are summed, and that sum is compared to the sum of the budgets for that tag during the same period, taking any exclusions or supersessions into account (definitions of these terms can be found below in "Exclusions, supersessions, and overlapping budgets").

### Budget definition
- A Timewarrior _tag_ is used as the key for a YAML dictionary which contains all budgets that apply to that tag and their properties. Within this dictionary, any number of budgets can be defined.
- Each budget contains the following:
    - A _start date_ when the budget takes effect, specified in ISO format using the ```date``` key. Budgets remain in effect until superseded by newer budgets. More info about that in the next section.
    - A _size_, expressed as some combination of ```hours```, ```minutes```, and ```seconds```. Integers or floats can be used as values for these.
    - Optionally, a list of days of the week to ```exclude``` from the budget, defined as a list of numbered days of the week to exclude (Monday = 0, Tuesday = 1, etc.).

### Exclusions, supersessions, and overlapping budgets
```timew-budget``` allows you to set multiple budgets for a single tag, which has two primary use cases:
1. Defining a budget that _supersedes_ an older budget while retaining the older budget, i.e. without making the new budget retroactive.
    - For example, if you decide to start training for a marathon taking place in April, you might want to increase the size of the ```workout``` budget starting in December to account for the higher training volume, without making it appear that the amount of time spent working out before December was underbudget.
2. Allocating different budget sizes to different days of the week. In ```timew-budget```, this is implemented using _exclusions_.
    - By default, a budget applies to every day of the week, but you can define specific days of the week that the budget does not apply to.
    - For example, if you want to work out on weekdays and rest on weekends, you can define a budget for the ```workout``` tag for 1 hour that excludes weekends, and another budget for that tag for 0 hours that excludes weekdays.
    - If a budget excludes a day of the week that is included in the report period, it won't be computed for that day. So if you invoke ```timew-budget``` for a week-long period using the above example, you'd get a total budget size of 5 hours (1 for each weekday and 0 for the weekend).
    - Importantly, if you log an interval with the ```workout``` tag on a weekend, it will be disregarded in a budget report that only includes Saturday and/or Sunday, since the ```workout``` budget for those days is 0. However, it *will* appear in a report including the whole week, even if you only work out on the weekend, since budgets are computed as the sum of all daily budgets over the report period against the sum of all intervals with the budgeted tag over that period.

```timew-budget``` can only apply one budget to a tag for each day during the report period, and budgets that directly overlap are not supported. Here is how it chooses a budget for the day if multiple budgets are defined for the tag:
1. Any future-dated budgets are disregarded since they haven't taken effect yet
2. Any budgets that exclude this day of the week are disregarded
3. If there are no budgets left after filtering 1 and 2, no budget is computed for the tag for that day
4. If there is one budget left, use that
5. If there is more than one budget left, use the newest one, which supersedes the others
6. If the remaining budgets have the same date, use the first one that was declared in the budget file.
    - Python's ```sort()``` is stable, so the first budget in the sorted list of budgets with the same date is also necessarily the one that was parsed first.

## Examples
All examples below are included in the provided ```timew-budget.yml``` file.

### A simple example
This budget applies to intervals tagged ```example```. A budget file consists of one of these sections for each budgeted tag, in this exact format.

```yml
example:                        # Example tag
  - date: 2025-01-01            # Effective January 1, 2025
    hours: 1                    # 1 hour, 33 minutes, and 7 seconds per day
    minutes: 33         
    seconds: 7
```

### An example of supersession
In this example, the second budget supersedes the first budget on February 1, so the first budget will not apply to any dates after January 30.

```yml
example2:
  - date: 2025-01-01            # Effective January 1, 2025
    hours: 1                    # 1 hour, 33 minutes, and 7 seconds per day
    minutes: 33         
    seconds: 7
  - date: 2025-02-01            # Effective February 1, 2025
    hours: 2                    # 2 hours per day
```

If you were to run a report from January 1 to February 28, you'd get a total ```example2``` budget size of 102h33m30s, which is 46h33m30s for all days in January (1h33m7s per day * 30 days) plus 56h for all days in February (2h per day * 28 days). That total size would be compared to the sum of all intervals tagged ```example2``` during the same period.

### An example of exclusions
These budgets use exclusions to define different budget sizes for different days of the week.

```yml
example3:
  - date: 2025-01-01            # Effective January 1, 2025
    exclude: [5, 6]             # Exclude Saturdays and Sundays
    hours: 1                    # 1 hour and 30 minutes per day
    minutes: 30  
  - date: 2025-01-01            # Effective January 1, 2025
    exclude: [0, 1, 2, 3, 4]    # Exclude weekdays
    hours: 2                    # 2 hours per day
```

If you were to run a report for any week after January 1, you'd get a total ```example3``` budget size of 11h30m, which is 7h30m for each weekday plus 2h for each weekend day.

### An example of overlapping budgets
These budgets overlap during the same dates. The second one will be ignored by ```timew-budget```.

```yml
example4:
  - date: 2025-01-01            # Effective January 1, 2025
    hours: 1                    # 1 hour, 33 minutes, and 7 seconds per day
    minutes: 33         
    seconds: 7
  - date: 2025-01-01            # Effective January 1, 2025
    hours: 2                    # 2 hours per day
```

## Future state and feature roadmap
- The parsing logic is a bit finicky and I haven't thoroughly tested it against malformed or incorrectly written budget files. More robust error handling is a top priority.
- The first iteration of this tool supported monthly and yearly budgets. I ended up removing these before the initial public release because I wasn't using them and I couldn't figure out a good way to unify them with day-of-week-based exclusions. I'm open to reimplementing them if a more general exclusions concept could be conceived.
- My initial exclusions implementation supported overlapping budgets that could be summed to a single budget, but I couldn't find a way to square this with support for budget supersession.

If you have any ideas, feature requests, bugs, etc. please open an issue or submit a PR. Thanks!

## References
[^1]: https://timewarrior.net/
[^2]: https://taskwarrior.org/
[^3]: https://timewarrior.net/docs/api/
[^4]: https://beancount.github.io/fava/
[^5]: https://beancount.github.io/
