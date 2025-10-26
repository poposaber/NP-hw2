from message_format import MessageFormat
import uuid
test_format = MessageFormat({
    "action": str,
    "username": str,
    "data": dict
})

print("Testing to_json:")
print(test_format.to_json("update_score", "play\"123\"er1", {"score": 100}))

print("Testing to_arg_list:")
json_str = test_format.to_json("update_score", "play\'234\"123\'234\"er1", {"score": 100})
#json_str = '{"action": "update_score", "username": "play\"123\"er1", "score": 100, "extra_field": "ignored"}'
action, username, data = test_format.to_arg_list(json_str)
print(action, username, data)

print(*[1, 2, 3])
print(uuid.uuid4().hex)
dict1 = {}
if dict1:
    print("dict1 is True")
else:
    print("dict1 is False")