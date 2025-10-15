import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

class FeedbackService:
    def __init__(self, feedback_dir: str = "data/feedback"):
        self.feedback_dir = feedback_dir
        self.daily_dir = os.path.join(feedback_dir, "daily")
        self.analytics_dir = os.path.join(feedback_dir, "analytics")

        os.makedirs(self.daily_dir, exist_ok=True)
        os.makedirs(self.analytics_dir, exist_ok=True)

        # Initialize daily analytics file
        self.today_analytics = self._get_today_analytics_file()

    def _get_today_analytics_file(self) -> str:
        """Get today's analytics file path"""
        today = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.analytics_dir, f"analytics_{today}.json")

    def _get_feedback_file(self, feedback_id: str) -> str:
        """Get feedback file path"""
        today = datetime.now().strftime("%Y-%m-%d")
        day_dir = os.path.join(self.daily_dir, today)
        os.makedirs(day_dir, exist_ok=True)
        return os.path.join(day_dir, f"{feedback_id}.json")

    def record_feedback(
        self,
        message_id: str,
        conversation_id: str,
        user_id: str,
        organization_id: str,
        query: str,
        response: str,
        feedback_type: str,
        rating: Optional[int] = None,
        correction: Optional[str] = None,
        comment: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Record user feedback on a response"""

        feedback_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        feedback_data = {
            "id": feedback_id,
            "message_id": message_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "organization_id": organization_id,
            "query": query,
            "response": response,
            "feedback_type": feedback_type,
            "rating": rating,
            "correction": correction,
            "comment": comment,
            "metadata": metadata or {},
            "timestamp": timestamp,
            "date": datetime.now().strftime("%Y-%m-%d")
        }

        # Save feedback to file
        feedback_file = self._get_feedback_file(feedback_id)
        with open(feedback_file, 'w') as f:
            json.dump(feedback_data, f, indent=2)

        # Update analytics
        self._update_analytics(feedback_data)

        print(f"Feedback recorded: {feedback_type} for message {message_id}")
        return feedback_data

    def record_thumbs_up(
        self,
        message_id: str,
        conversation_id: str,
        user_id: str,
        organization_id: str,
        query: str,
        response: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Record positive feedback"""
        return self.record_feedback(
            message_id=message_id,
            conversation_id=conversation_id,
            user_id=user_id,
            organization_id=organization_id,
            query=query,
            response=response,
            feedback_type="thumbs_up",
            rating=1,
            metadata=metadata
        )

    def record_thumbs_down(
        self,
        message_id: str,
        conversation_id: str,
        user_id: str,
        organization_id: str,
        query: str,
        response: str,
        comment: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Record negative feedback"""
        return self.record_feedback(
            message_id=message_id,
            conversation_id=conversation_id,
            user_id=user_id,
            organization_id=organization_id,
            query=query,
            response=response,
            feedback_type="thumbs_down",
            rating=-1,
            comment=comment,
            metadata=metadata
        )

    def record_correction(
        self,
        message_id: str,
        conversation_id: str,
        user_id: str,
        organization_id: str,
        query: str,
        response: str,
        correction: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Record user correction to a response"""
        return self.record_feedback(
            message_id=message_id,
            conversation_id=conversation_id,
            user_id=user_id,
            organization_id=organization_id,
            query=query,
            response=response,
            feedback_type="correction",
            rating=-1,
            correction=correction,
            metadata=metadata
        )

    def _update_analytics(self, feedback_data: Dict):
        """Update daily analytics with new feedback"""
        analytics_file = self.today_analytics

        # Load existing analytics
        if os.path.exists(analytics_file):
            with open(analytics_file, 'r') as f:
                analytics = json.load(f)
        else:
            analytics = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "total_feedback": 0,
                "thumbs_up": 0,
                "thumbs_down": 0,
                "corrections": 0,
                "by_organization": {},
                "by_intent": {},
                "by_query_type": {},
                "avg_confidence_positive": [],
                "avg_confidence_negative": [],
                "common_issues": []
            }

        # Update counts
        analytics["total_feedback"] += 1

        feedback_type = feedback_data.get("feedback_type", "")
        if feedback_type == "thumbs_up":
            analytics["thumbs_up"] += 1
        elif feedback_type == "thumbs_down":
            analytics["thumbs_down"] += 1
        elif feedback_type == "correction":
            analytics["corrections"] += 1

        # Update by organization
        org_id = feedback_data.get("organization_id", "unknown")
        if org_id not in analytics["by_organization"]:
            analytics["by_organization"][org_id] = {
                "total": 0,
                "positive": 0,
                "negative": 0
            }

        analytics["by_organization"][org_id]["total"] += 1
        if feedback_type == "thumbs_up":
            analytics["by_organization"][org_id]["positive"] += 1
        else:
            analytics["by_organization"][org_id]["negative"] += 1

        # Track confidence scores
        metadata = feedback_data.get("metadata", {})
        confidence = metadata.get("confidence_score", 0)
        if confidence > 0:
            if feedback_type == "thumbs_up":
                analytics["avg_confidence_positive"].append(confidence)
            else:
                analytics["avg_confidence_negative"].append(confidence)

        # Track by intent
        intent = metadata.get("intent", "unknown")
        if intent not in analytics["by_intent"]:
            analytics["by_intent"][intent] = {"positive": 0, "negative": 0}

        if feedback_type == "thumbs_up":
            analytics["by_intent"][intent]["positive"] += 1
        else:
            analytics["by_intent"][intent]["negative"] += 1

        # Save analytics
        with open(analytics_file, 'w') as f:
            json.dump(analytics, f, indent=2)

        print(f"Analytics updated: {analytics['total_feedback']} total feedback entries")

    def get_today_analytics(self) -> Dict:
        """Get today's analytics"""
        analytics_file = self.today_analytics

        if os.path.exists(analytics_file):
            with open(analytics_file, 'r') as f:
                analytics = json.load(f)

            # Calculate averages
            if analytics["avg_confidence_positive"]:
                analytics["avg_confidence_positive_value"] = sum(analytics["avg_confidence_positive"]) / len(analytics["avg_confidence_positive"])
            else:
                analytics["avg_confidence_positive_value"] = 0

            if analytics["avg_confidence_negative"]:
                analytics["avg_confidence_negative_value"] = sum(analytics["avg_confidence_negative"]) / len(analytics["avg_confidence_negative"])
            else:
                analytics["avg_confidence_negative_value"] = 0

            # Calculate success rate
            total = analytics["thumbs_up"] + analytics["thumbs_down"]
            if total > 0:
                analytics["success_rate"] = analytics["thumbs_up"] / total
            else:
                analytics["success_rate"] = 0

            return analytics

        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_feedback": 0,
            "success_rate": 0
        }

    def get_date_range_analytics(self, days: int = 7) -> List[Dict]:
        """Get analytics for the last N days"""
        analytics_list = []

        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            analytics_file = os.path.join(self.analytics_dir, f"analytics_{date}.json")

            if os.path.exists(analytics_file):
                with open(analytics_file, 'r') as f:
                    analytics = json.load(f)

                    # Calculate success rate
                    total = analytics.get("thumbs_up", 0) + analytics.get("thumbs_down", 0)
                    if total > 0:
                        analytics["success_rate"] = analytics.get("thumbs_up", 0) / total
                    else:
                        analytics["success_rate"] = 0

                    analytics_list.append(analytics)

        return analytics_list

    def get_feedback_for_training(self, limit: int = 100) -> List[Dict]:
        """Get recent feedback data for model fine-tuning"""
        training_data = []

        # Get all feedback files from today
        today = datetime.now().strftime("%Y-%m-%d")
        day_dir = os.path.join(self.daily_dir, today)

        if os.path.exists(day_dir):
            for filename in os.listdir(day_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(day_dir, filename)
                    with open(filepath, 'r') as f:
                        feedback = json.load(f)

                        # Format for training
                        if feedback.get("feedback_type") == "thumbs_up":
                            training_data.append({
                                "query": feedback["query"],
                                "response": feedback["response"],
                                "rating": "positive",
                                "metadata": feedback.get("metadata", {})
                            })
                        elif feedback.get("correction"):
                            training_data.append({
                                "query": feedback["query"],
                                "response": feedback["response"],
                                "corrected_response": feedback["correction"],
                                "rating": "negative_with_correction",
                                "metadata": feedback.get("metadata", {})
                            })

        return training_data[:limit]

    def cleanup_old_data(self, retention_days: int = 1):
        """Remove feedback data older than retention period"""
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        removed_count = 0

        # Clean up daily feedback
        if os.path.exists(self.daily_dir):
            for day_folder in os.listdir(self.daily_dir):
                day_path = os.path.join(self.daily_dir, day_folder)

                if os.path.isdir(day_path):
                    try:
                        folder_date = datetime.strptime(day_folder, "%Y-%m-%d")

                        if folder_date < cutoff_date:
                            # Remove all files in this day's folder
                            for filename in os.listdir(day_path):
                                filepath = os.path.join(day_path, filename)
                                os.remove(filepath)
                                removed_count += 1

                            # Remove the folder
                            os.rmdir(day_path)
                            print(f"Removed feedback folder: {day_folder}")
                    except ValueError:
                        continue

        # Clean up old analytics (keep more analytics history)
        analytics_retention = 30
        analytics_cutoff = datetime.now() - timedelta(days=analytics_retention)

        if os.path.exists(self.analytics_dir):
            for filename in os.listdir(self.analytics_dir):
                if filename.startswith("analytics_") and filename.endswith(".json"):
                    try:
                        date_str = filename.replace("analytics_", "").replace(".json", "")
                        file_date = datetime.strptime(date_str, "%Y-%m-%d")

                        if file_date < analytics_cutoff:
                            filepath = os.path.join(self.analytics_dir, filename)
                            os.remove(filepath)
                            print(f"Removed old analytics: {filename}")
                    except ValueError:
                        continue

        print(f"Cleanup complete: Removed {removed_count} feedback files")
        return removed_count

    def export_training_data(self, output_file: str):
        """Export all feedback data for training purposes"""
        all_training_data = []

        # Collect from all days
        if os.path.exists(self.daily_dir):
            for day_folder in os.listdir(self.daily_dir):
                day_path = os.path.join(self.daily_dir, day_folder)

                if os.path.isdir(day_path):
                    for filename in os.listdir(day_path):
                        if filename.endswith('.json'):
                            filepath = os.path.join(day_path, filename)
                            with open(filepath, 'r') as f:
                                feedback = json.load(f)

                                # Format for training
                                training_item = {
                                    "query": feedback["query"],
                                    "response": feedback["response"],
                                    "feedback_type": feedback["feedback_type"],
                                    "rating": feedback.get("rating", 0),
                                    "metadata": feedback.get("metadata", {}),
                                    "timestamp": feedback["timestamp"]
                                }

                                if feedback.get("correction"):
                                    training_item["corrected_response"] = feedback["correction"]

                                all_training_data.append(training_item)

        # Save to output file
        with open(output_file, 'w') as f:
            json.dump(all_training_data, f, indent=2)

        print(f"Exported {len(all_training_data)} training examples to {output_file}")
        return len(all_training_data)

    def get_problematic_queries(self, min_negative_feedback: int = 2) -> List[Dict]:
        """Identify queries that consistently receive negative feedback"""
        query_feedback = {}

        # Analyze all recent feedback
        if os.path.exists(self.daily_dir):
            for day_folder in os.listdir(self.daily_dir):
                day_path = os.path.join(self.daily_dir, day_folder)

                if os.path.isdir(day_path):
                    for filename in os.listdir(day_path):
                        if filename.endswith('.json'):
                            filepath = os.path.join(day_path, filename)
                            with open(filepath, 'r') as f:
                                feedback = json.load(f)

                                query = feedback["query"]
                                if query not in query_feedback:
                                    query_feedback[query] = {
                                        "query": query,
                                        "positive": 0,
                                        "negative": 0,
                                        "corrections": []
                                    }

                                if feedback["feedback_type"] == "thumbs_up":
                                    query_feedback[query]["positive"] += 1
                                else:
                                    query_feedback[query]["negative"] += 1

                                if feedback.get("correction"):
                                    query_feedback[query]["corrections"].append(feedback["correction"])

        # Filter problematic queries
        problematic = []
        for query_data in query_feedback.values():
            if query_data["negative"] >= min_negative_feedback:
                query_data["success_rate"] = query_data["positive"] / (query_data["positive"] + query_data["negative"])
                if query_data["success_rate"] < 0.5:
                    problematic.append(query_data)

        # Sort by negative count
        problematic.sort(key=lambda x: x["negative"], reverse=True)

        return problematic
