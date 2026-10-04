#include <unity.h>

#include <limits>
#include <string>

#include "backoff.h"
#include "telemetry.h"
#include "topics.h"

void test_device_ids() {
  TEST_ASSERT_TRUE(topics::valid_device_id("esp32-demo-01"));
  TEST_ASSERT_TRUE(topics::valid_device_id("a"));
  TEST_ASSERT_FALSE(topics::valid_device_id("bad/+"));
  TEST_ASSERT_FALSE(topics::valid_device_id("Upper"));
  TEST_ASSERT_FALSE(topics::valid_device_id(std::string(65, 'a')));
}

void test_topics() {
  TEST_ASSERT_EQUAL_STRING("iot/v1/devices/demo/telemetry", topics::telemetry("demo").c_str());
  TEST_ASSERT_EQUAL_STRING("iot/v1/devices/demo/config/ack", topics::config_ack("demo").c_str());
}

TelemetrySample fixture() {
  return {"esp32-demo-01", "boot-a", 42, std::nullopt, 3600, 22.4, 48.1, 1013.2, -56};
}

void test_telemetry_serialization_and_sequence() {
  auto sample = fixture();
  const auto payload = serialize_telemetry(sample);
  TEST_ASSERT_NOT_EQUAL(std::string::npos, payload.find("\"sequence\":42"));
  TEST_ASSERT_NOT_EQUAL(std::string::npos, payload.find("\"sampled_at\":null"));
  ++sample.sequence;
  TEST_ASSERT_NOT_EQUAL(payload, serialize_telemetry(sample));
}

void test_invalid_and_payload_limit() {
  auto sample = fixture();
  sample.temperature_c = std::numeric_limits<double>::infinity();
  TEST_ASSERT_FALSE(valid_telemetry(sample));
  TEST_ASSERT_TRUE(serialize_telemetry(sample).empty());
  TEST_ASSERT_LESS_THAN(1024, serialize_telemetry(fixture()).size());
}

void test_status_serialization() {
  const auto payload = serialize_status("demo", "boot-a", "online", "connected", "1.0.0");
  TEST_ASSERT_NOT_EQUAL(std::string::npos, payload.find("\"status\":\"online\""));
}

void test_config_validation() {
  TEST_ASSERT_TRUE(valid_interval(1));
  TEST_ASSERT_TRUE(valid_interval(3600));
  TEST_ASSERT_FALSE(valid_interval(0));
  TEST_ASSERT_FALSE(valid_interval(3601));
}

void test_backoff() {
  Backoff backoff(1000, 10000);
  TEST_ASSERT_EQUAL_UINT32(1000, backoff.next_delay());
  TEST_ASSERT_EQUAL_UINT32(2000, backoff.next_delay());
  TEST_ASSERT_EQUAL_UINT32(4000, backoff.next_delay());
  TEST_ASSERT_EQUAL_UINT32(8000, backoff.next_delay());
  TEST_ASSERT_EQUAL_UINT32(10000, backoff.next_delay());
  backoff.reset();
  TEST_ASSERT_EQUAL_UINT32(1100, backoff.next_delay(100));
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_device_ids);
  RUN_TEST(test_topics);
  RUN_TEST(test_telemetry_serialization_and_sequence);
  RUN_TEST(test_invalid_and_payload_limit);
  RUN_TEST(test_status_serialization);
  RUN_TEST(test_config_validation);
  RUN_TEST(test_backoff);
  return UNITY_END();
}

