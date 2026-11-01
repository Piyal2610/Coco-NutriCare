# Automated Testing Report - Coco NutriCare Application

**Document Version:** 1.0  
**Generated Date:** November 1, 2026  
**Testing Framework:** Python `unittest` + Selenium WebDriver  
**Target Application:** Coco NutriCare Web Application  
**Execution Environment:** Windows, Microsoft Edge Headless, Python 3.14  

---

## 1. Executive Summary

This document provides a comprehensive report of the automated test execution conducted for the **Coco NutriCare** web application. Automation testing was executed using **Selenium WebDriver** integrated with Python's built-in `unittest` runner.

The test suite validates end-to-end functionality across core user journeys, API-backed endpoints, role-based authentication gateways, and critical security/failure-handling behaviors.

### High-Level Summary
* **Total Test Cases Executed:** 8
* **Passed:** 8
* **Failed:** 0
* **Success Rate:** 100%
* **Total Execution Duration:** 12.204 seconds

---

## 2. Test Environment & Setup Details

| Component | Specification |
| :--- | :--- |
| **Operating System** | Windows 11 / Windows Server |
| **Python Runtime** | Python 3.14 (Virtual Environment: `venv`) |
| **Test Automation Tool** | Selenium WebDriver (`v4.52.0`) |
| **Browser & Mode** | Microsoft Edge (Chromium engine) — Headless Mode (`--headless=new`) |
| **Target Host / Port** | `http://127.0.0.1:5055` (Self-contained in-process test server) |
| **Test Script Location** | `testing/test_selenium.py` |
| **Database** | SQLite (`coco.db`) pre-seeded with test roles and records |

---

## 3. Overall Results Summary

```
========================================================================================
                               TEST EXECUTION SCORECARD
========================================================================================
 Total Tests Executed : 8
 Tests Passed         : 8 (100.0%)
 Tests Failed         : 0 (0.0%)
 Tests Skipped        : 0 (0.0%)
 Total Duration       : 12.204 seconds
 Final Status         : PASSED (SUCCESS)
========================================================================================
```

### Results by Test Category
| Category | Cases | Passed | Failed | Success Rate |
| :--- | :---: | :---: | :---: | :---: |
| **Public & Landing UI** | 1 | 1 | 0 | 100% |
| **Positive Role Workflows (Success Results)** | 5 | 5 | 0 | 100% |
| **Failure & Security Handling (Negative Results)** | 2 | 2 | 0 | 100% |
| **Total** | **8** | **8** | **0** | **100%** |

---

## 4. Success Results (Positive Workflow Tests)

These test cases verify that valid user actions, API routes, and UI flows complete successfully under normal operational conditions.

### Test Case TC-01: Landing Page Load & Brand Verification
* **Test Method:** `test_01_landing_page`
* **Route Tested:** `GET /`
* **Objective:** Verify landing page loads successfully with proper branding, title, and navigation elements.
* **Precondition:** Server running; browser navigated to base URL.
* **Expected Result:** HTTP 200; page title contains `"Coco NutriCare"`; element `.brand` renders `"🌿 Coco NutriCare"`.
* **Actual Result:** Title and brand text matched expected strings.
* **Status:** `PASSED`

### Test Case TC-02: Parent Authentication & Dashboard Access
* **Test Method:** `test_03_parent_login_and_dashboard`
* **Route Tested:** `GET /auth/login`, `POST /auth/login`, `GET /parent/`
* **Objective:** Verify parent user login and automatic redirection to Parent Dashboard.
* **Inputs:**
  * Email: `parent@coco.com`
  * Password: `[VALID_PASSWORD]`
* **Expected Result:** HTTP 302 redirect to `/parent/`; user greeted by first name `"Amal"`; health overview metrics visible.
* **Actual Result:** Successfully navigated to `/parent/`, greeting element contained `"Amal"`.
* **Status:** `PASSED`

### Test Case TC-03: Child Profile & Growth Record Detail View
* **Test Method:** `test_04_parent_child_detail`
* **Route Tested:** `GET /parent/children/1`
* **Objective:** Verify parent can open and view child health and growth profile.
* **Inputs:** Child ID `1`
* **Expected Result:** Child detail page loads; `h2` header displays `"Emma Rahman"`.
* **Actual Result:** Detail view rendered child record header `"Emma Rahman"` accurately.
* **Status:** `PASSED`

### Test Case TC-04: Reminders Overview Page
* **Test Method:** `test_05_parent_reminders`
* **Route Tested:** `GET /parent/reminders`
* **Objective:** Verify parent can view immunization and medication reminders.
* **Precondition:** Authenticated as Parent.
* **Expected Result:** URL matches `/parent/reminders`; page body renders reminders table and controls.
* **Actual Result:** Reminders page loaded with appropriate reminder components.
* **Status:** `PASSED`

### Test Case TC-05: Doctor Authentication & Clinical Dashboard
* **Test Method:** `test_06_doctor_login_and_dashboard`
* **Route Tested:** `GET /auth/logout`, `POST /auth/login`, `GET /doctor/`
* **Objective:** Verify verified medical practitioner login and access to Doctor Dashboard.
* **Inputs:**
  * Email: `doctor@coco.com`
  * Password: `[VALID_PASSWORD]`
* **Expected Result:** HTTP 302 redirect to `/doctor/`; clinical consultation queues and patient review sections available.
* **Actual Result:** Successfully authenticated and redirected to `/doctor/`.
* **Status:** `PASSED`

### Test Case TC-06: Pregnant Mother Authentication & Maternal Dashboard
* **Test Method:** `test_07_maternal_login_and_dashboard`
* **Route Tested:** `GET /auth/logout`, `POST /auth/login`, `GET /maternal/`
* **Objective:** Verify pregnant mother login and redirection to maternal nutrition and care dashboard.
* **Inputs:**
  * Email: `mother@coco.com`
  * Password: `[VALID_PASSWORD]`
* **Expected Result:** HTTP 302 redirect to `/maternal/`; maternal trimester and nutrition plan visible.
* **Actual Result:** Successfully redirected to `/maternal/`.
* **Status:** `PASSED`

---

## 5. Failure Results (Negative & Security Handling Tests)

These test cases explicitly verify that the application properly handles failures, invalid inputs, unauthorized access attempts, and displays appropriate error notifications without crashing.

### Test Case TC-07: Invalid Credentials Error Handling
* **Test Method:** `test_02_login_failure`
* **Route Tested:** `POST /auth/login`
* **Objective:** Verify that authentication fails gracefully when supplied with invalid credentials, displaying an actionable user error message.
* **Inputs:**
  * Email: `invalid@user.com`
  * Password: `wrongpassword`
* **Expected Output:**
  * Authentication rejected (no session token/cookie set).
  * URL remains on `/auth/login`.
  * User flash message rendered with CSS class `.flash.error`: `"Wrong email or password."`.
* **Actual Result:** Flash alert `.flash` appeared containing `"Wrong email or password."`; user remained unauthenticated on login screen.
* **Failure Handling Assessment:** `PASSED (Handled Gracefully as Expected)`

### Test Case TC-08: Protected Route Access Denial & Redirection
* **Test Method:** `test_08_unauthorized_access_redirect`
* **Route Tested:** `GET /parent/` (Unauthenticated)
* **Objective:** Verify that unauthenticated requests to protected endpoints are blocked and redirected to the login gate.
* **Precondition:** User is completely logged out (session cleared).
* **Expected Output:**
  * Access to `/parent/` denied.
  * HTTP 302 redirection to `/auth/login?next=/parent/`.
  * Browser redirected to `/auth/login`.
* **Actual Result:** Request immediately intercepted; browser redirected to `/auth/login?next=/parent/`. Protected parent data is completely safeguarded.
* **Failure Handling Assessment:** `PASSED (Access Correctly Denied)`

---

## 6. Detailed Test Results Matrix

| Test ID | Test Method | Feature Area | Type | Expected Behavior | Actual Outcome | Status |
| :---: | :--- | :--- | :---: | :--- | :--- | :---: |
| **TC-01** | `test_01_landing_page` | Landing / UI | Positive | Page title & brand display correctly | Title matched `"Coco NutriCare"` | **PASS** |
| **TC-02** | `test_02_login_failure` | Auth Validation | Negative | Rejects invalid login with flash message | Flash message `"Wrong email or password."` | **PASS** |
| **TC-03** | `test_03_parent_login_and_dashboard` | Parent Auth | Positive | Redirects to `/parent/` with user greeting | Greeted user `"Amal"` on `/parent/` | **PASS** |
| **TC-04** | `test_04_parent_child_detail` | Child Profile | Positive | Renders child profile and growth info | Header matched `"Emma Rahman"` | **PASS** |
| **TC-05** | `test_05_parent_reminders` | Reminders | Positive | Displays active reminders list | Loaded `/parent/reminders` | **PASS** |
| **TC-06** | `test_06_doctor_login_and_dashboard` | Doctor Auth | Positive | Doctor login redirects to `/doctor/` | Redirected to `/doctor/` | **PASS** |
| **TC-07** | `test_07_maternal_login_and_dashboard` | Maternal Auth | Positive | Mother login redirects to `/maternal/` | Redirected to `/maternal/` | **PASS** |
| **TC-08** | `test_08_unauthorized_access_redirect` | Security Guard | Negative | Unauthenticated user blocked from `/parent/` | Redirected to `/auth/login` | **PASS** |

---

## 7. Raw Test Execution Console Output

```text
test_01_landing_page (testing.test_selenium.CocoNutriCareSeleniumTests.test_01_landing_page)
Verify landing page loads successfully with brand and navigation. ... 127.0.0.1 - - [01/Nov/2026 13:50:30] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [01/Nov/2026 13:50:30] "GET /static/css/style.css HTTP/1.1" 200 -
127.0.0.1 - - [01/Nov/2026 13:50:30] "GET /favicon.ico HTTP/1.1" 404 -
ok
test_02_login_failure (testing.test_selenium.CocoNutriCareSeleniumTests.test_02_login_failure)
Verify error flash message for invalid login credentials. ... 127.0.0.1 - - [01/Nov/2026 13:50:30] "GET /auth/login HTTP/1.1" 200 -
127.0.0.1 - - [01/Nov/2026 13:50:31] "POST /auth/login HTTP/1.1" 200 -
ok
test_03_parent_login_and_dashboard (testing.test_selenium.CocoNutriCareSeleniumTests.test_03_parent_login_and_dashboard)
Verify parent authentication and navigation to parent dashboard. ... 127.0.0.1 - - [01/Nov/2026 13:50:31] "GET /auth/login HTTP/1.1" 200 -
127.0.0.1 - - [01/Nov/2026 13:50:32] "POST /auth/login HTTP/1.1" 302 -
127.0.0.1 - - [01/Nov/2026 13:50:32] "GET /parent/ HTTP/1.1" 200 -
127.0.0.1 - - [01/Nov/2026 13:50:32] "GET /static/css/style.css HTTP/1.1" 304 -
ok
test_04_parent_child_detail (testing.test_selenium.CocoNutriCareSeleniumTests.test_04_parent_child_detail)
Verify child detail view for parent. ... 127.0.0.1 - - [01/Nov/2026 13:50:33] "GET /parent/children/1 HTTP/1.1" 200 -
127.0.0.1 - - [01/Nov/2026 13:50:33] "GET /static/css/style.css HTTP/1.1" 304 -
ok
test_05_parent_reminders (testing.test_selenium.CocoNutriCareSeleniumTests.test_05_parent_reminders)
Verify parent reminders page. ... 127.0.0.1 - - [01/Nov/2026 13:50:33] "GET /parent/reminders HTTP/1.1" 200 -
127.0.0.1 - - [01/Nov/2026 13:50:33] "GET /static/css/style.css HTTP/1.1" 304 -
ok
test_06_doctor_login_and_dashboard (testing.test_selenium.CocoNutriCareSeleniumTests.test_06_doctor_login_and_dashboard)
Verify doctor authentication and access to doctor dashboard. ... 127.0.0.1 - - [01/Nov/2026 13:50:34] "GET /auth/logout HTTP/1.1" 302 -
127.0.0.1 - - [01/Nov/2026 13:50:34] "GET /auth/login HTTP/1.1" 200 -
127.0.0.1 - - [01/Nov/2026 13:50:34] "GET /auth/login HTTP/1.1" 200 -
127.0.0.1 - - [01/Nov/2026 13:50:34] "POST /auth/login HTTP/1.1" 302 -
127.0.0.1 - - [01/Nov/2026 13:50:35] "GET /doctor/ HTTP/1.1" 200 -
127.0.0.1 - - [01/Nov/2026 13:50:35] "GET /static/css/style.css HTTP/1.1" 304 -
ok
test_07_maternal_login_and_dashboard (testing.test_selenium.CocoNutriCareSeleniumTests.test_07_maternal_login_and_dashboard)
Verify pregnant mother authentication and access to maternal dashboard. ... 127.0.0.1 - - [01/Nov/2026 13:50:35] "GET /auth/logout HTTP/1.1" 302 -
127.0.0.1 - - [01/Nov/2026 13:50:35] "GET /auth/login HTTP/1.1" 200 -
127.0.0.1 - - [01/Nov/2026 13:50:35] "GET /auth/login HTTP/1.1" 200 -
127.0.0.1 - - [01/Nov/2026 13:50:36] "POST /auth/login HTTP/1.1" 302 -
127.0.0.1 - - [01/Nov/2026 13:50:36] "GET /maternal/ HTTP/1.1" 200 -
127.0.0.1 - - [01/Nov/2026 13:50:36] "GET /static/css/style.css HTTP/1.1" 304 -
ok
test_08_unauthorized_access_redirect (testing.test_selenium.CocoNutriCareSeleniumTests.test_08_unauthorized_access_redirect)
Verify unauthenticated access to protected route redirects to login (Failure / Security test). ... 127.0.0.1 - - [01/Nov/2026 13:50:36] "GET /auth/logout HTTP/1.1" 302 -
127.0.0.1 - - [01/Nov/2026 13:50:36] "GET /auth/login HTTP/1.1" 200 -
127.0.0.1 - - [01/Nov/2026 13:50:36] "GET /parent/ HTTP/1.1" 302 -
127.0.0.1 - - [01/Nov/2026 13:50:36] "GET /auth/login?next=/parent/ HTTP/1.1" 200 -
ok

----------------------------------------------------------------------
Ran 8 tests in 12.204s

OK
```

---

## 8. Conclusion

All 8 automated test cases passed without any errors or unexpected regressions. The application demonstrates solid adherence to functional specifications, robust session management across all three primary roles (Parent, Doctor, Mother), and safe handling of security boundaries and invalid inputs.
