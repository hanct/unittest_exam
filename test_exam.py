import pytest
from unittest.mock import Mock, patch
from typing import List

from exam import (
    Order,
    OrderProcessingService,
    APIResponse,
    APIException,
    DatabaseException,
    DatabaseService,
    APIClient
)


class MockDatabaseService(DatabaseService):
    def __init__(self, orders: List[Order] = None):
        self.orders = orders or []
        self.updated_orders = []

    def get_orders_by_user(self, user_id: int) -> List[Order]:
        return self.orders

    def update_order_status(self, order_id: int, status: str, priority: str) -> bool:
        self.updated_orders.append((order_id, status, priority))
        return True


class MockAPIClient(APIClient):
    def __init__(self, response: APIResponse = None, should_raise: bool = False):
        self.response = response
        self.should_raise = should_raise

    def call_api(self, order_id: int) -> APIResponse:
        if self.should_raise:
            raise APIException()
        return self.response


def test_should_return_false_when_user_has_no_orders():
    # Arrange
    db_service = MockDatabaseService(orders=[])
    api_client = MockAPIClient()
    service = OrderProcessingService(db_service, api_client)

    # Act
    result = service.process_orders(user_id=1)

    # Assert
    assert result is False


def test_should_create_csv_and_mark_exported_when_type_a_order_amount_less_than_150():
    # Arrange
    order = Order(id=1, type='A', amount=100.0, flag=False)
    db_service = MockDatabaseService(orders=[order])
    api_client = MockAPIClient()
    service = OrderProcessingService(db_service, api_client)

    # Act
    with patch('builtins.open', new_callable=Mock) as mock_open:
        service.process_orders(user_id=1)

    # Assert
    assert order.status == 'exported'
    assert len(db_service.updated_orders) == 1
    assert db_service.updated_orders[0][1] == 'exported'


def test_should_create_csv_with_high_value_note_when_type_a_order_amount_greater_than_150():
    # Arrange
    order = Order(id=1, type='A', amount=200.0, flag=False)
    db_service = MockDatabaseService(orders=[order])
    api_client = MockAPIClient()
    service = OrderProcessingService(db_service, api_client)

    # Act
    with patch('builtins.open', new_callable=Mock) as mock_open:
        service.process_orders(user_id=1)

    # Assert
    assert order.status == 'exported'
    assert len(db_service.updated_orders) == 1
    assert db_service.updated_orders[0][1] == 'exported'


def test_should_mark_export_failed_when_type_a_order_file_writing_fails():
    # Arrange
    order = Order(id=1, type='A', amount=100.0, flag=False)
    db_service = MockDatabaseService(orders=[order])
    api_client = MockAPIClient()
    service = OrderProcessingService(db_service, api_client)

    # Act
    with patch('builtins.open', side_effect=IOError):
        service.process_orders(user_id=1)

    # Assert
    assert order.status == 'export_failed'
    assert len(db_service.updated_orders) == 1
    assert db_service.updated_orders[0][1] == 'export_failed'


def test_should_mark_processed_when_type_b_order_api_success_data_ge_50_and_amount_lt_100():
    # Arrange
    order = Order(id=1, type='B', amount=80.0, flag=False)
    db_service = MockDatabaseService(orders=[order])
    api_client = MockAPIClient(response=APIResponse('success', 60))
    service = OrderProcessingService(db_service, api_client)

    # Act
    service.process_orders(user_id=1)

    # Assert
    assert order.status == 'processed'
    assert len(db_service.updated_orders) == 1
    assert db_service.updated_orders[0][1] == 'processed'


def test_should_mark_pending_when_type_b_order_api_success_data_lt_50():
    # Arrange
    order = Order(id=1, type='B', amount=80.0, flag=False)
    db_service = MockDatabaseService(orders=[order])
    api_client = MockAPIClient(response=APIResponse('success', 40))
    service = OrderProcessingService(db_service, api_client)

    # Act
    service.process_orders(user_id=1)

    # Assert
    assert order.status == 'pending'
    assert len(db_service.updated_orders) == 1
    assert db_service.updated_orders[0][1] == 'pending'


def test_should_mark_pending_when_type_b_order_api_success_and_flag_is_true():
    # Arrange
    order = Order(id=1, type='B', amount=80.0, flag=True)
    db_service = MockDatabaseService(orders=[order])
    api_client = MockAPIClient(response=APIResponse('success', 60))
    service = OrderProcessingService(db_service, api_client)

    # Act
    service.process_orders(user_id=1)

    # Assert
    assert order.status == 'pending'
    assert len(db_service.updated_orders) == 1
    assert db_service.updated_orders[0][1] == 'pending'


def test_should_mark_error_when_type_b_order_api_success_but_no_conditions_match():
    # Arrange
    order = Order(id=1, type='B', amount=120.0, flag=False)
    db_service = MockDatabaseService(orders=[order])
    api_client = MockAPIClient(response=APIResponse('success', 60))
    service = OrderProcessingService(db_service, api_client)

    # Act
    service.process_orders(user_id=1)

    # Assert
    assert order.status == 'error'
    assert len(db_service.updated_orders) == 1
    assert db_service.updated_orders[0][1] == 'error'


def test_should_mark_api_error_when_type_b_order_api_returns_failure():
    # Arrange
    order = Order(id=1, type='B', amount=80.0, flag=False)
    db_service = MockDatabaseService(orders=[order])
    api_client = MockAPIClient(response=APIResponse('failure', 60))
    service = OrderProcessingService(db_service, api_client)

    # Act
    service.process_orders(user_id=1)

    # Assert
    assert order.status == 'api_error'
    assert len(db_service.updated_orders) == 1
    assert db_service.updated_orders[0][1] == 'api_error'


def test_should_mark_api_failure_when_type_b_order_api_raises_exception():
    # Arrange
    order = Order(id=1, type='B', amount=80.0, flag=False)
    db_service = MockDatabaseService(orders=[order])
    api_client = MockAPIClient(should_raise=True)
    service = OrderProcessingService(db_service, api_client)

    # Act
    service.process_orders(user_id=1)

    # Assert
    assert order.status == 'api_failure'
    assert len(db_service.updated_orders) == 1
    assert db_service.updated_orders[0][1] == 'api_failure'


def test_should_mark_completed_when_type_c_order_flag_is_true():
    # Arrange
    order = Order(id=1, type='C', amount=80.0, flag=True)
    db_service = MockDatabaseService(orders=[order])
    api_client = MockAPIClient()
    service = OrderProcessingService(db_service, api_client)

    # Act
    service.process_orders(user_id=1)

    # Assert
    assert order.status == 'completed'
    assert len(db_service.updated_orders) == 1
    assert db_service.updated_orders[0][1] == 'completed'


def test_should_mark_in_progress_when_type_c_order_flag_is_false():
    # Arrange
    order = Order(id=1, type='C', amount=80.0, flag=False)
    db_service = MockDatabaseService(orders=[order])
    api_client = MockAPIClient()
    service = OrderProcessingService(db_service, api_client)

    # Act
    service.process_orders(user_id=1)

    # Assert
    assert order.status == 'in_progress'
    assert len(db_service.updated_orders) == 1
    assert db_service.updated_orders[0][1] == 'in_progress'


def test_should_mark_unknown_type_when_order_type_is_unknown():
    # Arrange
    order = Order(id=1, type='D', amount=80.0, flag=False)
    db_service = MockDatabaseService(orders=[order])
    api_client = MockAPIClient()
    service = OrderProcessingService(db_service, api_client)

    # Act
    service.process_orders(user_id=1)

    # Assert
    assert order.status == 'unknown_type'
    assert len(db_service.updated_orders) == 1
    assert db_service.updated_orders[0][1] == 'unknown_type'


def test_should_set_low_priority_when_order_amount_less_than_200():
    # Arrange
    order = Order(id=1, type='A', amount=150.0, flag=False)
    db_service = MockDatabaseService(orders=[order])
    api_client = MockAPIClient()
    service = OrderProcessingService(db_service, api_client)

    # Act
    with patch('builtins.open', new_callable=Mock):
        service.process_orders(user_id=1)

    # Assert
    assert order.priority == 'low'
    assert len(db_service.updated_orders) == 1
    assert db_service.updated_orders[0][2] == 'low'


def test_should_set_high_priority_when_order_amount_greater_than_200():
    # Arrange
    order = Order(id=1, type='A', amount=250.0, flag=False)
    db_service = MockDatabaseService(orders=[order])
    api_client = MockAPIClient()
    service = OrderProcessingService(db_service, api_client)

    # Act
    with patch('builtins.open', new_callable=Mock):
        service.process_orders(user_id=1)

    # Assert
    assert order.priority == 'high'
    assert len(db_service.updated_orders) == 1
    assert db_service.updated_orders[0][2] == 'high'


def test_should_mark_db_error_when_database_update_raises_exception():
    # Arrange
    order = Order(id=1, type='A', amount=100.0, flag=False)
    db_service = MockDatabaseService(orders=[order])
    db_service.update_order_status = Mock(side_effect=DatabaseException)
    api_client = MockAPIClient()
    service = OrderProcessingService(db_service, api_client)

    # Act
    with patch('builtins.open', new_callable=Mock):
        service.process_orders(user_id=1)

    # Assert
    assert order.status == 'db_error'


def test_should_return_false_when_unexpected_exception_occurs():
    # Arrange
    order = Order(id=1, type='A', amount=100.0, flag=False)
    db_service = MockDatabaseService(orders=[order])
    db_service.get_orders_by_user = Mock(side_effect=Exception)
    api_client = MockAPIClient()
    service = OrderProcessingService(db_service, api_client)

    # Act
    result = service.process_orders(user_id=1)

    # Assert
    assert result is False
