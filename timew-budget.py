#!/usr/bin/python3

# timew-budget.py
# Copyright © 2025 Kiernan Roche under the MIT License
# This extension compares time intervals tracked in Timewarrior over a given period to the budgets defined in a budget file, which is specified in the Timewarrior config.
# Please see the README and example timew-budget.yml file for correct syntax and general information.

import sys, calendar, datetime, json, yaml
from tabulate import tabulate

def parse_config_line(line):
    # split by ": " delimiter
    try:
        return line.rstrip().split("\u003a\u0020", 1)
    except ValueError as e:
        return e

def parse_intervals(intervals):
    intervals_dict = None

    try:
        intervals_dict = json.loads(intervals)
    except:
        print("Could not load intervals into dict. Syntax error?", file=sys.stderr)

    return intervals_dict

def parse_budgets(handle):
    with handle as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as e:
            print(e, file=sys.stderr)
    return None

def print_report(mapping, report_start, report_end):
    # mapping[tag][0] is budget size, in seconds
    # mapping[tag][1] is actual time spent, in seconds
    budget_size_total   = 0 
    actual_time_total   = 0
    rows = []
    
    for tag in mapping.keys():
        # Format the budget size as HH:MM:SS
        seconds = mapping[tag][0]
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        budget_size_fmt = "{:02}:{:02}:{:02}".format(int(hours), int(minutes), int(seconds))
        budget_size_total += mapping[tag][0]
        
        # Format the actual time spent as HH:MM:SS
        seconds = mapping[tag][1]
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        actual_time_fmt = "{:02}:{:02}:{:02}".format(int(hours), int(minutes), int(seconds))
        actual_time_total += mapping[tag][1]
        
        # Calculate net time spent and format it as HH:MM:SS
        net = mapping[tag][0] - mapping[tag][1]
        seconds = abs(net)
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        net_fmt = f"{'-' if net < 0 else ''}" + "{:02}:{:02}:{:02}".format(int(hours), int(minutes), int(seconds))
        net_percentage = round((mapping[tag][1] / mapping[tag][0]) * 100, 2)
        net_percentage_fmt = str(net_percentage) + "%"

        rows.append([tag, actual_time_fmt, budget_size_fmt, net_fmt, net_percentage_fmt])
    
    # Format totals
    seconds = budget_size_total
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    budget_size_total_fmt = "{:02}:{:02}:{:02}".format(int(hours), int(minutes), int(seconds))
    
    seconds = actual_time_total
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    actual_time_total_fmt = "{:02}:{:02}:{:02}".format(int(hours), int(minutes), int(seconds))
    
    seconds = budget_size_total - actual_time_total
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    net_total_fmt = f"{'-' if net < 0 else '{:02}:{:02}:{:02}'}".format(int(hours), int(minutes), int(seconds))
    rows.append(["", "", "", "", ""])
    rows.append(["Total", actual_time_total_fmt, budget_size_total_fmt, net_total_fmt, str(round((actual_time_total / budget_size_total) * 100, 2)) + "%"])

    print(tabulate(rows, headers=["Tag", "Time spent", "Budgeted time", "Budget surplus", "Utilization"]))
    print()
    print("Budget report for period " + str(report_start) + " to " + str(report_end))

def main():
    # timewarrior config
    config = {}

    # intervals
    intervals = []
    
    # budgets
    budgets = {}

    # parse config block
    for line in iter(sys.stdin.readline, ''):
        # if we have reached the blank line that separates the config block from the interval block,
        if len(line.strip()) == 0:
            # break the loop and start processing the intervals in the next loop block
            break
        else:
            try:
                config_line = parse_config_line(line)
                try:
                    config[config_line[0]] = config_line[1]
                except:
                    continue
            # error parsing configs
            except Exception as e:
                print(e, file=sys.stderr)
                return
            finally:
                continue
    
    # parse interval block
    try:
        intervals = parse_intervals(''.join(sys.stdin.readlines()).rstrip())
    except Exception as e:
        print(e, file=sys.stderr)
        return
    
    # parse budgets from file
    try:
        budget_file_handle = open(config["budget.file"], 'r')
        budgets = parse_budgets(budget_file_handle)
    except Exception as e:
        print("Could not open budget file. Is it declared correctly in your Timewarrior config?", file=sys.stderr)
        return

    # core logic

    # fetch dates
    # by default, the report should be for today only
    if "temp.report.start" not in config or "temp.report.end" not in config:
        print("Report range not specified. Please specify a range or use a range hint.", file=sys.stderr)
        return
    else:
        report_start = datetime.datetime.fromisoformat(config["temp.report.start"])
        report_end = datetime.datetime.fromisoformat(config["temp.report.end"])

    report_duration_days = (report_end.date() - report_start.date()).days

    if report_duration_days < 1:
        print("Budget report does not support a duration smaller than one day.", file=sys.stderr)
        return

    date_range = [report_start.date() + datetime.timedelta(days=x) for x in range(0, report_duration_days)]

    # calculate budget values
    # this variable contains a mapping of each budget tag to a tuple of budget size, in seconds, and actual time spent, in seconds
    budgets_mapping = {}
    
    for tag in budgets.keys():
        # Total budget size, in seconds. This is the sum of budget seconds per day, for all days of the report.
        budget_size_total   = 0
        # Actual time spent against the budget, in seconds. This is the sum of the durations of all the intervals in the report with the budget tag.
        time_spent_total    = 0
        
        budgets_dated = sorted(budgets[tag], key=lambda b: b["date"], reverse=True)
        
        for date in date_range:
            # only consider budgets that are dated today or earlier and don't exclude this date's day of the week
            budgets_dated_prior = [b for b in budgets_dated if (date - b["date"]).days >= 0 and ("exclude" not in b or date.weekday() not in b["exclude"])]
            budget = None
            # if there is no budget that applies to the date, skip to the next iteration
            if len(budgets_dated_prior) == 0:
                continue
            # otherwise, use the first parsed budget that doesn't exclude this date's day of the week
            else:
                budget = budgets_dated_prior[0]
            
            # convert the budget size to seconds
            budget_size = 0

            if "hours" in budget:
                budget_size += budget["hours"] * 3600
            if "minutes" in budget:
                budget_size += budget["minutes"] * 60
            if "seconds" in budget:
                budget_size += budget["seconds"]

            # catch budgets with undefined size
            if not "hours" in budget and not "minutes" in budget and not "seconds" in budget:
                print("Budget starting " + str(budget["date"]) + " for tag " + tag + " has no defined size. Please fix or remove it.", file=sys.stderr)
                return
            
            # add budget size to total
            budget_size_total += budget_size
        
        # catch zero budgets
        if budget_size_total == 0:
            continue

        # only consider intervals with the same tag as this budget
        tagged_intervals = [interval for interval in intervals if tag in interval["tags"]]
        if len(tagged_intervals) > 0:
            # for each interval tagged with the budget's tag:
            for interval in tagged_intervals:
                # trim interval start time to report start time
                interval_start = datetime.datetime.fromisoformat(interval["start"])
                if interval_start < report_start:
                    interval_start = report_start
                # if the interval is open, time spent is the time from the start of the interval to now or the end of the report period, whichever comes first
                now = datetime.datetime.now(datetime.timezone.utc)
                if report_end < now:
                    time_spent = report_end - interval_start
                else:
                    time_spent = now - interval_start
                # but if the interval is closed, calculate the delta between the start and end times instead
                if "end" in interval:
                    # trim interval end time to report end time
                    interval_end = datetime.datetime.fromisoformat(interval["end"])
                    if interval_end > report_end:
                        interval_end = report_end
                    time_spent = interval_end - interval_start
                # add the delta to total time spent
                time_spent_total += time_spent.total_seconds()
        
        # round budget size total to nearest int
        budget_size_total = round(budget_size_total)
        time_spent_total = round(time_spent_total)
        
        # add results to budgets_mapping
        budgets_mapping[tag] = (budget_size_total, time_spent_total)

    # print budget report
    print_report(budgets_mapping, report_start, report_end)

    return

if __name__ == '__main__':
    main()
