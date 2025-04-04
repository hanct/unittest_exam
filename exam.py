import csv
import time

from abc import ABC, abstractmethod
from typing import List, Any


class Order:
	def __init__(self, id: int, type: str, amount: float, flag: bool):
		self.id = id
		self.type = type
		self.amount = amount
		self.flag = flag
		self.status = 'new'
		self.priority = 'low'


class APIResponse:
	def __init__(self, status: str, data: Any):
		self.status = status
		self.data = data


class APIException(Exception):
	pass


class DatabaseException(Exception):
	pass


class DatabaseService(ABC):
	@abstractmethod
	def get_orders_by_user(self, user_id: int) -> List[Order]:
		pass

	@abstractmethod
	def update_order_status(self, order_id: int, status: str, priority: str) -> bool:
		pass


class APIClient(ABC):
	@abstractmethod
	def call_api(self, order_id: int) -> APIResponse:
		pass


class OrderProcessingService:
	def __init__(self, db_service: DatabaseService, api_client: APIClient):
		self.db_service = db_service
		self.api_client = api_client

	def process_orders(self, user_id: int) -> bool:
		try:
			orders = self.db_service.get_orders_by_user(user_id)

			if not orders:
				return False

			for order in orders:
				if order.type == 'A':
					csv_file = f'orders_type_A_{user_id}_{int(time.time())}.csv'
					try:
						with open(csv_file, 'w', newline='') as file_handle:
							writer = csv.writer(file_handle)
							writer.writerow(['ID', 'Type', 'Amount', 'Flag', 'Status', 'Priority'])

							writer.writerow([
								order.id,
								order.type,
								order.amount,
								str(order.flag).lower(),
								order.status,
								order.priority
							])

							if order.amount > 150:
								writer.writerow(['', '', '', '', 'Note', 'High value order'])

						order.status = 'exported'
					except IOError:
						order.status = 'export_failed'

				elif order.type == 'B':
					try:
						api_response = self.api_client.call_api(order.id)

						if api_response.status == 'success':
							if api_response.data >= 50 and order.amount < 100:
								order.status = 'processed'
							elif api_response.data < 50 or order.flag:
								order.status = 'pending'
							else:
								order.status = 'error'
						else:
							order.status = 'api_error'
					except APIException:
						order.status = 'api_failure'

				elif order.type == 'C':
					if order.flag:
						order.status = 'completed'
					else:
						order.status = 'in_progress'
				else:
					order.status = 'unknown_type'

				if order.amount > 200:
					order.priority = 'high'
				else:
					order.priority = 'low'

				try:
					self.db_service.update_order_status(order.id, order.status, order.priority)
				except DatabaseException:
					order.status = 'db_error'

			return True
		except Exception:
			return False