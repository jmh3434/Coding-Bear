# Create this file at: my_app/management/commands/seed_challenges.py

from django.core.management.base import BaseCommand
from my_app.models import CodeChallenge

class Command(BaseCommand):
    help = 'Seed the database with sample coding challenges'

    def handle(self, *args, **options):
        challenges = [
            {
                'title': 'Two Sum',
                'description': '''Given an array of integers and a target sum, return the indices of two numbers that add up to the target.

You may assume that each input would have exactly one solution, and you may not use the same element twice.

Example:
Given nums = [2, 7, 11, 15], target = 9
Because nums[0] + nums[1] = 2 + 7 = 9, return [0, 1]''',
                'difficulty': 'easy',
                'input_example': 'nums = [2, 7, 11, 15]\ntarget = 9',
                'output_example': '[0, 1]',
                'solution': '''def two_sum(nums, target):
    num_map = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in num_map:
            return [num_map[complement], i]
        num_map[num] = i
    return []''',
                'is_standalone': True,
                'tags': 'arrays, hash-table, easy',
            },
            {
                'title': 'Reverse String',
                'description': '''Write a function that reverses a string. The input string is given as an array of characters.

Do not allocate extra space for another array. You must modify the input array in-place with O(1) extra memory.

Example:
Input: ["h","e","l","l","o"]
Output: ["o","l","l","e","h"]''',
                'difficulty': 'easy',
                'input_example': '["h","e","l","l","o"]',
                'output_example': '["o","l","l","e","h"]',
                'solution': '''def reverse_string(s):
    left, right = 0, len(s) - 1
    while left < right:
        s[left], s[right] = s[right], s[left]
        left += 1
        right -= 1
    return s''',
                'is_standalone': True,
                'tags': 'strings, two-pointers',
            },
            {
                'title': 'Valid Parentheses',
                'description': '''Given a string containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.

An input string is valid if:
1. Open brackets must be closed by the same type of brackets.
2. Open brackets must be closed in the correct order.

Example:
Input: "()[]{}"
Output: true

Input: "([)]"
Output: false''',
                'difficulty': 'easy',
                'input_example': '"()[]{}"',
                'output_example': 'true',
                'solution': '''def is_valid(s):
    stack = []
    mapping = {")": "(", "}": "{", "]": "["}
    
    for char in s:
        if char in mapping:
            if not stack or stack.pop() != mapping[char]:
                return False
        else:
            stack.append(char)
    
    return not stack''',
                'is_standalone': True,
                'tags': 'strings, stack',
            },
            {
                'title': 'Maximum Subarray',
                'description': '''Given an integer array nums, find the contiguous subarray (containing at least one number) which has the largest sum and return its sum.

Example:
Input: [-2,1,-3,4,-1,2,1,-5,4]
Output: 6
Explanation: [4,-1,2,1] has the largest sum = 6.

Follow up: If you have figured out the O(n) solution, try coding another solution using the divide and conquer approach.''',
                'difficulty': 'medium',
                'input_example': '[-2,1,-3,4,-1,2,1,-5,4]',
                'output_example': '6',
                'solution': '''def max_subarray(nums):
    max_sum = current_sum = nums[0]
    
    for num in nums[1:]:
        current_sum = max(num, current_sum + num)
        max_sum = max(max_sum, current_sum)
    
    return max_sum''',
                'is_standalone': True,
                'tags': 'arrays, dynamic-programming',
            },
            {
                'title': 'Fibonacci Number',
                'description': '''The Fibonacci numbers, commonly denoted F(n) form a sequence, called the Fibonacci sequence, such that each number is the sum of the two preceding ones, starting from 0 and 1.

F(0) = 0, F(1) = 1
F(n) = F(n - 1) + F(n - 2), for n > 1.

Given n, calculate F(n).

Example:
Input: n = 4
Output: 3
Explanation: F(4) = F(3) + F(2) = 2 + 1 = 3.''',
                'difficulty': 'easy',
                'input_example': '4',
                'output_example': '3',
                'solution': '''def fibonacci(n):
    if n <= 1:
        return n
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    
    return b''',
                'is_standalone': True,
                'tags': 'math, dynamic-programming, recursion',
            },
            {
                'title': 'Merge Two Sorted Lists',
                'description': '''You are given the heads of two sorted linked lists list1 and list2.

Merge the two lists in a one sorted list. The list should be made by splicing together the nodes of the first two lists.

Return the head of the merged linked list.

For this challenge, represent the linked list as a simple array.

Example:
Input: list1 = [1,2,4], list2 = [1,3,4]
Output: [1,1,2,3,4,4]''',
                'difficulty': 'easy',
                'input_example': 'list1 = [1,2,4]\nlist2 = [1,3,4]',
                'output_example': '[1,1,2,3,4,4]',
                'solution': '''def merge_two_lists(list1, list2):
    result = []
    i = j = 0
    
    while i < len(list1) and j < len(list2):
        if list1[i] <= list2[j]:
            result.append(list1[i])
            i += 1
        else:
            result.append(list2[j])
            j += 1
    
    result.extend(list1[i:])
    result.extend(list2[j:])
    
    return result''',
                'is_standalone': True,
                'tags': 'linked-list, recursion, two-pointers',
            },
        ]

        created_count = 0
        for challenge_data in challenges:
            challenge, created = CodeChallenge.objects.get_or_create(
                title=challenge_data['title'],
                defaults=challenge_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created challenge: {challenge.title}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Challenge already exists: {challenge.title}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} new challenges!'
            )
        )